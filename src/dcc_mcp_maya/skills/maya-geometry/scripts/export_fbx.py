"""Export the current Maya scene (or current selection) to FBX.

Why this script grew
--------------------
The previous implementation called ``cmds.file(path, options="v=0;",
type="FBX export", exportAll=True)`` and trusted Maya's defaults.  In
practice that meant:

* No ``FBXExportBakeComplexAnimation`` → the FBX did not contain the
  baked keyframes generated upstream by the workflow, so the import
  side saw geometry but no animation.
* No control over ``FBXExportFileVersion`` → using whatever version
  the FBX plugin happens to default to, which may be older than the
  receiving DCC supports (or newer than older Maya/MotionBuilder
  builds can read).
* No verification that the file was actually written.

This rewrite:

1. Drops every export setting through the official ``mel.eval(...)``
   ``FBXExport*`` global option vars (the only documented contract for
   the FBX plugin's option store).
2. Resets the option store via ``FBXResetExport`` first so we never
   inherit stale settings from a previous artist export.
3. Verifies the destination after the call: existence + non-zero size,
   and reports the size back so the agent can sanity-check.
4. Surfaces the full applied-options dict in the success envelope so
   downstream tools (and the caller's audit log) can see exactly what
   was written.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

logger = logging.getLogger(__name__)

#: Allowed values for ``up_axis``.  Maya's FBX plugin accepts only the
#: literal strings ``y`` and ``z`` (lower-case).
_VALID_UP_AXES = ("y", "z")

#: Allowed values for ``fbx_version``.  Tracks the FBX SDK version
#: strings the plugin has shipped with for at least the last 4 Maya LTS
#: cycles.  ``None`` means "leave the plugin default in place".
_VALID_FBX_VERSIONS = (
    "FBX202000",
    "FBX201900",
    "FBX201800",
    "FBX201600",
    "FBX201400",
)


def _ensure_plugin(cmds: Any, plugin_name: str) -> None:
    """Idempotently load the FBX plugin.

    ``loadPlugin`` is **not** safe to call repeatedly on every export
    so we query first.  Any failure surfaces as a Python exception that
    the caller's ``try`` block converts to a structured error.
    """
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def _coerce_bool_param(value: Any, name: str) -> bool:
    """Strict boolean coercion for ``mel.eval`` flag arguments.

    ``mel.eval('FBXExportFoo -v X')`` interprets *any* non-empty token
    as truthy, so we reject anything that isn't unambiguously a bool.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    raise ValueError("Parameter '{}' must be a boolean, got {!r}".format(name, value))


def _apply_fbx_options(  # noqa: PLR0913, PLR0912 — option mapping is intrinsically wide
    mel: Any,
    *,
    bake_animation: bool,
    start_frame: Optional[int],
    end_frame: Optional[int],
    step: int,
    up_axis: Optional[str],
    embed_media: bool,
    fbx_version: Optional[str],
    cameras: bool,
    lights: bool,
    constraints: bool,
    smoothing_groups: bool,
    triangulate: bool,
    instances: bool,
    tangents_binormals: bool,
) -> Dict[str, Any]:
    """Push every FBX option to the plugin's option store via MEL.

    Returns the dict of options actually applied so the caller can
    embed it in the success envelope for audit / debugging.

    Notes
    -----
    Each option is a separate ``mel.eval`` call because the FBX plugin
    parses the trailing ``-v <value>`` form one at a time.  We
    deliberately do *not* concatenate them into a single MEL string so
    a malformed value fails loud at the call site, not silently inside
    the plugin.
    """
    mel.eval("FBXResetExport")
    applied: Dict[str, Any] = {}

    def _send(option: str, value: Any) -> None:
        mel.eval("{} -v {}".format(option, value))
        applied[option] = value

    _send("FBXExportBakeComplexAnimation", "true" if bake_animation else "false")
    if bake_animation:
        if start_frame is not None:
            _send("FBXExportBakeComplexStart", int(start_frame))
        if end_frame is not None:
            _send("FBXExportBakeComplexEnd", int(end_frame))
        _send("FBXExportBakeComplexStep", int(step))
    _send("FBXExportCameras", "true" if cameras else "false")
    _send("FBXExportLights", "true" if lights else "false")
    _send("FBXExportConstraints", "true" if constraints else "false")
    _send("FBXExportSmoothingGroups", "true" if smoothing_groups else "false")
    _send("FBXExportTriangulate", "true" if triangulate else "false")
    _send("FBXExportInstances", "true" if instances else "false")
    _send("FBXExportTangents", "true" if tangents_binormals else "false")
    _send("FBXExportSmoothMesh", "true")
    _send("FBXExportEmbeddedTextures", "true" if embed_media else "false")

    if up_axis is not None:
        if up_axis not in _VALID_UP_AXES:
            raise ValueError(
                "Unsupported up_axis {!r}; expected one of {}".format(up_axis, _VALID_UP_AXES),
            )
        mel.eval("FBXExportUpAxis {}".format(up_axis))
        applied["FBXExportUpAxis"] = up_axis

    if fbx_version is not None:
        if fbx_version not in _VALID_FBX_VERSIONS:
            raise ValueError(
                "Unsupported fbx_version {!r}; expected one of {}".format(fbx_version, _VALID_FBX_VERSIONS),
            )
        # FBXExportFileVersion takes a quoted string.
        mel.eval('FBXExportFileVersion -v "{}"'.format(fbx_version))
        applied["FBXExportFileVersion"] = fbx_version

    return applied


def _normalize_path(path: str) -> str:
    """Expand ``~`` and ``$ENV`` and convert backslashes to forward slashes.

    Maya's ``cmds.file`` is happiest with forward-slashed absolute
    paths on every OS.  We don't ``os.path.abspath`` because the agent
    may legitimately pass a relative path — let Maya resolve against
    the current workspace root.
    """
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded.replace("\\", "/")


def _verify_output(path: str) -> Tuple[bool, int]:
    """Return ``(exists, size_bytes)`` for the FBX path."""
    if not os.path.exists(path):
        return False, 0
    return True, os.path.getsize(path)


def export_fbx(  # noqa: PLR0913 — parameter set is the public contract
    path: str,
    selected_only: bool = False,
    *,
    bake_animation: bool = True,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    step: int = 1,
    up_axis: Optional[str] = None,
    embed_media: bool = False,
    fbx_version: Optional[str] = None,
    ascii: bool = False,
    cameras: bool = True,
    lights: bool = True,
    constraints: bool = True,
    smoothing_groups: bool = True,
    triangulate: bool = False,
    instances: bool = False,
    tangents_binormals: bool = False,
) -> Dict[str, Any]:
    """Export the active Maya scene (or current selection) to FBX.

    Parameters
    ----------
    path
        Destination ``.fbx`` path.  Created or overwritten.
    selected_only
        Export the current selection instead of the whole scene.
    bake_animation
        If ``True`` (default) the export bakes complex animation into
        per-frame keyframes.  Required when the scene contains
        constraints / IK / driven keys / expressions whose evaluated
        result must survive the round-trip.
    start_frame, end_frame, step
        Override Maya's playback range when ``bake_animation`` is on.
        ``None`` falls back to the current playback range.
    up_axis
        ``"y"`` or ``"z"``.  ``None`` = leave plugin default.
    embed_media
        Embed referenced textures in the FBX.
    fbx_version
        One of :data:`_VALID_FBX_VERSIONS`; e.g. ``"FBX202000"``.
    ascii
        Write the FBX in ASCII format (debugging) instead of binary.
    cameras, lights, constraints, smoothing_groups, triangulate, instances, tangents_binormals
        FBX feature toggles forwarded to ``FBXExport*`` options.

    Returns
    -------
    dict
        ``maya_success`` envelope with ``context`` keys: ``path``,
        ``size_bytes``, ``selected_only``, ``applied_options``,
        ``ascii``.  On failure returns ``maya_error`` /
        ``maya_from_exception`` with ``context.path`` populated so the
        agent can re-try at a different location.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not path:
            return skill_error(
                "Missing path",
                "path is required",
                possible_solutions=["Pass an absolute or workspace-relative .fbx path"],
            )

        normalized = _normalize_path(path)
        parent_dir = os.path.dirname(normalized)
        if parent_dir and not os.path.isdir(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except OSError as exc:
                return skill_error(
                    "Cannot create output directory",
                    str(exc),
                    path=normalized,
                    possible_solutions=["Verify write permissions on the parent directory"],
                )

        try:
            _ensure_plugin(cmds, "fbxmaya")
        except Exception as exc:  # noqa: BLE001
            return skill_error(
                "FBX plugin unavailable",
                "loadPlugin('fbxmaya') failed: {}".format(exc),
                path=normalized,
                possible_solutions=[
                    "Install / enable Maya's bundled FBX plugin via Plug-in Manager",
                    "Run Maya with --gui at least once to register the plugin",
                ],
            )

        applied: Dict[str, Any] = _apply_fbx_options(
            mel,
            bake_animation=_coerce_bool_param(bake_animation, "bake_animation"),
            start_frame=start_frame,
            end_frame=end_frame,
            step=int(step),
            up_axis=up_axis,
            embed_media=_coerce_bool_param(embed_media, "embed_media"),
            fbx_version=fbx_version,
            cameras=_coerce_bool_param(cameras, "cameras"),
            lights=_coerce_bool_param(lights, "lights"),
            constraints=_coerce_bool_param(constraints, "constraints"),
            smoothing_groups=_coerce_bool_param(smoothing_groups, "smoothing_groups"),
            triangulate=_coerce_bool_param(triangulate, "triangulate"),
            instances=_coerce_bool_param(instances, "instances"),
            tangents_binormals=_coerce_bool_param(tangents_binormals, "tangents_binormals"),
        )

        # ``cmds.file`` honours options string for legacy reasons; we
        # already pushed everything through MEL globals so v=0 is fine.
        export_kwargs: Dict[str, Any] = {
            "force": True,
            "options": "v=0;",
            "type": "FBX export",
        }
        if selected_only:
            export_kwargs["exportSelected"] = True
        else:
            export_kwargs["exportAll"] = True
        if ascii:
            # Maya's FBX plugin recognises ``-ea`` via the type string.
            export_kwargs["type"] = "FBX export"
            mel.eval("FBXExportInAscii -v true")
            applied["FBXExportInAscii"] = "true"

        cmds.file(normalized, **export_kwargs)

        exists, size_bytes = _verify_output(normalized)
        if not exists:
            return skill_error(
                "FBX export reported success but the file is missing",
                "{} does not exist after cmds.file(...)".format(normalized),
                path=normalized,
                applied_options=applied,
            )
        if size_bytes == 0:
            return skill_error(
                "FBX export wrote a 0-byte file",
                "{} exists but has size 0".format(normalized),
                path=normalized,
                applied_options=applied,
                possible_solutions=[
                    "Check the Script Editor for FBX plugin warnings",
                    "Reduce the export to a known-good selection and retry",
                ],
            )

        return skill_success(
            "Exported FBX",
            path=normalized,
            size_bytes=size_bytes,
            selected_only=bool(selected_only),
            ascii=bool(ascii),
            applied_options=applied,
            prompt="Use maya_geometry__file_exists or import_fbx on another instance to verify the round-trip.",
        )
    except ImportError:
        return skill_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy with the FBX plugin available"],
        )
    except ValueError as exc:
        return skill_error(
            "Invalid FBX export parameter",
            str(exc),
            path=path,
        )
    except Exception as exc:  # noqa: BLE001 — relay traceback to client
        return skill_exception(exc, message="Failed to export FBX")


def _suggested_param_help() -> List[str]:
    """Return a list of examples used by the entry point's error envelope."""
    return [
        "export_fbx(path='C:/tmp/scene.fbx', bake_animation=True, start_frame=1, end_frame=120)",
        "export_fbx(path='/tmp/sel.fbx', selected_only=True, fbx_version='FBX202000')",
    ]


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`export_fbx`."""
    return export_fbx(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
