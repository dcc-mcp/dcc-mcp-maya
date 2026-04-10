"""Export selected objects or specified objects to Alembic (.abc) format."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def export_alembic(
    objects: List[str],
    file_path: str,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    world_space: bool = True,
    uv_write: bool = True,
) -> dict:
    """Export objects to Alembic archive.

    Args:
        objects: List of object names to export.
        file_path: Destination ``.abc`` file path.
        start_frame: Start frame for the export range (defaults to current timeline start).
        end_frame: End frame for the export range (defaults to current timeline end).
        world_space: If ``True``, export in world space.
        uv_write: If ``True``, include UV data in the export.

    Returns:
        ActionResultModel dict with ``context.file_path`` and ``context.object_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result("No objects specified", "Provide at least one object to export.").to_dict()
    if not file_path:
        return error_result("No file path specified", "Provide a valid .abc file path.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Verify all objects exist
        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(", ".join(missing)),
                "Check object names and try again.",
            ).to_dict()

        # Load AbcExport plugin if needed
        if not cmds.pluginInfo("AbcExport", query=True, loaded=True):
            cmds.loadPlugin("AbcExport")

        sf = start_frame if start_frame is not None else cmds.playbackOptions(query=True, min=True)
        ef = end_frame if end_frame is not None else cmds.playbackOptions(query=True, max=True)

        root_flags = " ".join("-root {}".format(obj) for obj in objects)
        ws_flag = "-worldSpace " if world_space else ""
        uv_flag = "-uvWrite " if uv_write else ""
        job_str = "{ws}{uv}-frameRange {sf} {ef} {roots} -file {fp}".format(
            ws=ws_flag,
            uv=uv_flag,
            sf=sf,
            ef=ef,
            roots=root_flags,
            fp=file_path,
        )
        cmds.AbcExport(jobArg=job_str)

        return success_result(
            "Exported {} object(s) to '{}'".format(len(objects), file_path),
            prompt="Alembic exported. Use import_alembic to load the file in another scene.",
            file_path=file_path,
            object_count=len(objects),
            start_frame=sf,
            end_frame=ef,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_alembic failed")
        return error_result("Failed to export Alembic", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return export_alembic(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(export_alembic(["pSphere1"], "/tmp/test.abc")))
