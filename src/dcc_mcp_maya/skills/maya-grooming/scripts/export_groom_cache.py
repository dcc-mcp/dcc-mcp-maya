"""Export an XGen interactive groom cache to disk."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def export_groom_cache(
    groom_node: str,
    file_path: str,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
) -> dict:
    """Export an XGen interactive groom cache (.igc) to disk.

    Args:
        groom_node: Name of the groom shape or transform.
        file_path: Output file path (should end in ``.igc``).
        start_frame: Start frame for cache export; defaults to scene start.
        end_frame: End frame for cache export; defaults to scene end.

    Returns:
        ActionResultModel dict with ``context.file_path`` and ``context.frame_range``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not groom_node:
        return error_result("No groom node specified", "Provide the groom shape or transform name.").to_dict()
    if not file_path:
        return error_result("No file path specified", "Provide a valid output file path.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(groom_node):
            return error_result(
                "Groom node '{}' does not exist".format(groom_node),
                "Check the node name with list_groomables.",
            ).to_dict()

        scene_start = cmds.playbackOptions(query=True, min=True)
        scene_end = cmds.playbackOptions(query=True, max=True)
        sf = start_frame if start_frame is not None else scene_start
        ef = end_frame if end_frame is not None else scene_end

        cmds.igExportGroom(
            groom_node,
            file=file_path,
            startFrame=sf,
            endFrame=ef,
        )

        return success_result(
            "Exported groom cache for '{}' to '{}'".format(groom_node, file_path),
            prompt=(
                "Cache exported. Import with igImportGroom or share with other artists."
            ),
            file_path=file_path,
            frame_range=[sf, ef],
            groom_node=groom_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_groom_cache failed")
        return error_result("Failed to export groom cache", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return export_groom_cache(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(export_groom_cache("groomDescription1", "/tmp/groom.igc")))
