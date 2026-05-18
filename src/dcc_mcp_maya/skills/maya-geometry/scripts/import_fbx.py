"""Import an FBX file into the current Maya scene.

The companion to :mod:`export_fbx`.  The previous skill family only
exposed export tools, which forced agents to drop into
``execute_python`` for every round-trip — losing schema validation,
``ToolAnnotations`` safety hints, and the structured error envelope.

Design choices
--------------
* The FBX plugin is loaded on first use so importing into an
  otherwise pristine ``mayapy`` session works.
* Imported nodes are returned both as short names (for follow-up tool
  calls) and as long DAG paths (for unambiguous selection).
* ``namespace`` defaults to ``None`` (= no namespace) but the agent
  is encouraged to pass one to keep multiple imports separable.
* ``group_name`` (post-import grouping) is optional; when supplied we
  make sure the new group is the first child of the world root for
  predictable hierarchy regardless of the FBX's own root layout.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

logger = logging.getLogger(__name__)


def _ensure_plugin(cmds: Any, plugin_name: str) -> None:
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def _normalize_path(path: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded.replace("\\", "/")


def _short_name(node: str) -> str:
    """Return the leaf component of a Maya DAG path."""
    return node.rsplit("|", 1)[-1] if "|" in node else node


def _select_difference(before: Sequence[str], after: Sequence[str]) -> List[str]:
    """Return nodes present in *after* but not in *before*.

    Maya's ``cmds.file(..., returnNewNodes=True)`` is the canonical
    way to do this, but it returns nodes only when the import succeeds
    *and* the plugin populates the list correctly — older FBX plugin
    builds occasionally return ``None``.  Using a set diff against a
    pre-import snapshot is robust against that.
    """
    before_set = set(before)
    return [n for n in after if n not in before_set]


def import_fbx(  # noqa: PLR0913 — public skill contract
    path: str,
    namespace: Optional[str] = None,
    group_name: Optional[str] = None,
    *,
    merge_namespaces: bool = False,
    generate_log: bool = False,
    take: Optional[int] = None,
) -> Dict[str, Any]:
    """Import *path* into the current scene and return the new nodes.

    Parameters
    ----------
    path
        Source ``.fbx`` path.  Must exist.
    namespace
        Optional namespace prefix for imported nodes (Maya creates it
        if missing).  Pass ``None`` for no namespace.
    group_name
        When set, the imported top-level transforms are re-parented
        under a new ``group_name`` transform at the scene root.  Useful
        for keeping multiple FBX imports separable in the outliner.
    merge_namespaces
        When ``True``, an existing namespace is reused instead of
        Maya generating a numeric suffix (``ns:``, ``ns1:``, …).
    generate_log
        Forwarded to ``FBXImportGenerateLog`` — turn on for verbose
        Script Editor diagnostics on a stuck import.
    take
        FBX "take" index (1-based) for files containing multiple
        animation takes.  ``None`` keeps the plugin default.

    Returns
    -------
    dict
        ``maya_success`` envelope with ``context`` keys ``path``,
        ``namespace``, ``imported_short_names``, ``imported_long_names``,
        ``top_level_groups`` and ``size_bytes``.
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
        if not os.path.exists(normalized):
            return skill_error(
                "FBX file not found",
                "{} does not exist on disk".format(normalized),
                path=normalized,
                possible_solutions=[
                    "Verify the path",
                    "If the file was just exported, call file_exists first",
                ],
            )

        try:
            _ensure_plugin(cmds, "fbxmaya")
        except Exception as exc:  # noqa: BLE001
            return skill_error(
                "FBX plugin unavailable",
                "loadPlugin('fbxmaya') failed: {}".format(exc),
                path=normalized,
            )

        # Configure import options through the plugin's MEL globals.
        mel.eval("FBXResetImport")
        mel.eval("FBXImportMode -v add")
        mel.eval("FBXImportMergeAnimationLayers -v true")
        mel.eval("FBXImportGenerateLog -v {}".format("true" if generate_log else "false"))
        if take is not None:
            mel.eval("FBXImportSetTake -ti {}".format(int(take)))

        before = cmds.ls(long=True) or []

        import_kwargs: Dict[str, Any] = {
            "i": True,  # invariant alias for `import=True`
            "type": "FBX",
            "ignoreVersion": True,
            "options": "fbx",
            "preserveReferences": True,
            "prompt": False,
        }
        if namespace:
            import_kwargs["namespace"] = namespace
            if not merge_namespaces:
                import_kwargs["renamingPrefix"] = namespace
            import_kwargs["mergeNamespacesOnClash"] = bool(merge_namespaces)

        try:
            cmds.file(normalized, **import_kwargs)
        except RuntimeError as exc:
            return skill_exception(
                exc,
                message="cmds.file import raised",
                path=normalized,
            )

        after = cmds.ls(long=True) or []
        new_long = _select_difference(before, after)
        new_short = sorted({_short_name(n) for n in new_long})

        # Optional re-grouping of new top-level transforms.
        top_level: List[str] = []
        if group_name:
            top_level_candidates = [n for n in new_long if n.count("|") == 1 and cmds.objectType(n) == "transform"]
            if top_level_candidates:
                created_group = cmds.group(top_level_candidates, name=group_name, world=True)
                top_level.append(created_group)
        else:
            top_level = sorted(
                {"|" + _short_name(n) for n in new_long if n.count("|") == 1 and cmds.objectType(n) == "transform"}
            )

        return skill_success(
            "Imported FBX",
            path=normalized,
            size_bytes=os.path.getsize(normalized),
            namespace=namespace,
            imported_short_names=new_short,
            imported_long_names=new_long,
            top_level_groups=top_level,
            prompt="Use maya_scene__find_by_pattern or get_selection to inspect the imported hierarchy.",
        )
    except ImportError:
        return skill_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy with the FBX plugin available"],
        )
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to import FBX")


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`import_fbx`."""
    return import_fbx(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
