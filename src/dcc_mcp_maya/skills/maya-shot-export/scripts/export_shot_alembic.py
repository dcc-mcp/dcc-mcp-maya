"""Export selected objects as an Alembic (.abc) sequence."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def export_shot_alembic(
    file_path: str,
    objects: Optional[List[str]] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    world_space: bool = True,
    uv_write: bool = True,
) -> dict:
    """Export selected objects as an Alembic (.abc) sequence.

    Args:
        file_path: Output ``.abc`` file path.
        objects: Objects to export.  If None, current selection is used.
        start_frame: Start frame.  Defaults to timeline start.
        end_frame: End frame.  Defaults to timeline end.
        world_space: Write geometry in world space.  Default: True.
        uv_write: Write UV sets.  Default: True.

    Returns:
        ActionResultModel dict with ``context.file_path`` and frame range.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if objects:
            targets = objects
        else:
            targets = cmds.ls(selection=True) or []
        if not targets:
            return skill_error(
                "Nothing selected",
                "Provide 'objects' or select nodes in Maya",
            )

        sf = start_frame if start_frame is not None else cmds.playbackOptions(q=True, minTime=True)
        ef = end_frame if end_frame is not None else cmds.playbackOptions(q=True, maxTime=True)

        out_dir = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(out_dir, exist_ok=True)

        # Load AbcExport plugin if needed
        if not cmds.pluginInfo("AbcExport", q=True, loaded=True):
            cmds.loadPlugin("AbcExport")

        root_flags = " ".join(["-root {}".format(obj) for obj in targets])
        ws_flag = "-worldSpace" if world_space else ""
        uv_flag = "-uvWrite" if uv_write else ""

        job_str = '-frameRange {sf} {ef} {ws} {uv} {roots} -file "{fp}"'.format(
            sf=int(sf),
            ef=int(ef),
            ws=ws_flag,
            uv=uv_flag,
            roots=root_flags,
            fp=file_path.replace("\\", "/"),
        )
        cmds.AbcExport(j=job_str)

        return skill_success(
            "Exported Alembic to '{}'".format(file_path),
            prompt="Use import_file to bring the Alembic back into a scene.",
            file_path=file_path,
            start_frame=sf,
            end_frame=ef,
            objects=targets,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to export Alembic")


@skill_entry
def main(**kwargs):
    return export_shot_alembic(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
