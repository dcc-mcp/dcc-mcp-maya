"""Export geometry to Alembic (.abc) format.

Why this script exists
----------------------
The ``import_file.py`` script in this skill already handles Alembic *import*
(loading the ``AbcImport`` plugin).  This script covers the export side
using ``cmds.AbcExport`` with sensible defaults.

.. note::
    For shot-level Alembic export with timeline/frame-range control, prefer
    ``maya_shot_export__export_shot_alembic`` which is purpose-built for
    sequence export workflows.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import Any, Dict, List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _normalize_path(path: str) -> str:
    """Expand ``~`` and ``$ENV`` and convert backslashes to forward slashes."""
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded.replace("\\", "/")


def _ensure_plugin(cmds: Any, plugin_name: str) -> None:
    """Idempotently load an Alembic plugin."""
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def export_alembic(
    file_path: str,
    objects: Optional[List[str]] = None,
    world_space: bool = True,
    uv_write: bool = True,
    write_visibility: bool = True,
) -> Dict[str, Any]:
    """Export selected (or specified) objects as an Alembic (.abc) file.

    Parameters
    ----------
    file_path
        Destination ``.abc`` path.  Created or overwritten.
    objects
        Objects to export.  If ``None``, the current selection is used.
    world_space
        Write geometry in world space.  Default: ``True``.
    uv_write
        Write UV sets.  Default: ``True``.
    write_visibility
        Write visibility state.  Default: ``True``.

    Returns
    -------
    dict
        ``skill_success`` envelope with ``context`` keys: ``file_path``,
        ``size_bytes``, ``objects``, ``world_space``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not file_path:
            return skill_error(
                "Missing file_path",
                "file_path is required",
                possible_solutions=["Provide an absolute or workspace-relative .abc path"],
            )

        normalized = _normalize_path(file_path)
        parent_dir = os.path.dirname(normalized)
        if parent_dir and not os.path.isdir(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except OSError as exc:
                return skill_error(
                    "Cannot create output directory",
                    str(exc),
                    file_path=normalized,
                    possible_solutions=["Verify write permissions on the parent directory"],
                )

        try:
            _ensure_plugin(cmds, "AbcExport")
        except Exception as exc:  # noqa: BLE001
            return skill_error(
                "Alembic export plugin unavailable",
                "loadPlugin('AbcExport') failed: {}".format(exc),
                file_path=normalized,
                possible_solutions=[
                    "Install / enable Maya's bundled AbcExport plugin via Plug-in Manager",
                ],
            )

        if objects:
            targets = objects
        else:
            targets = cmds.ls(selection=True) or []
        if not targets:
            return skill_error(
                "Nothing to export",
                "Provide 'objects' or select nodes in Maya before exporting",
                possible_solutions=[
                    "Select geometry in the viewport and retry",
                    "Pass objects=['pCube1', 'pSphere1'] to export specific nodes",
                ],
            )

        # Build the AbcExport job string.
        root_flags = " ".join(["-root {}".format(obj) for obj in targets])
        flags = [root_flags]
        if world_space:
            flags.append("-worldSpace")
        if uv_write:
            flags.append("-uvWrite")
        if write_visibility:
            flags.append("-writeVisibility")

        job_str = '{} -file "{}"'.format(" ".join(flags), normalized)
        cmds.AbcExport(j=job_str)

        # Verify output.
        if not os.path.exists(normalized):
            return skill_error(
                "Alembic export reported success but the file is missing",
                "{} does not exist after AbcExport".format(normalized),
                file_path=normalized,
            )
        size_bytes = os.path.getsize(normalized)
        if size_bytes == 0:
            return skill_error(
                "Alembic export wrote a 0-byte file",
                "{} exists but has size 0".format(normalized),
                file_path=normalized,
                possible_solutions=[
                    "Check the Script Editor for AbcExport warnings",
                    "Reduce the export to a known-good selection and retry",
                ],
            )

        return skill_success(
            "Exported Alembic ({:,} bytes, {} object(s))".format(size_bytes, len(targets)),
            file_path=normalized,
            size_bytes=size_bytes,
            objects=targets,
            count=len(targets),
            world_space=world_space,
            uv_write=uv_write,
            write_visibility=write_visibility,
            prompt="Use maya_geometry__import_file to bring the Alembic back into a scene.",
        )
    except ImportError:
        return skill_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to export Alembic")


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`export_alembic`."""
    return export_alembic(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
