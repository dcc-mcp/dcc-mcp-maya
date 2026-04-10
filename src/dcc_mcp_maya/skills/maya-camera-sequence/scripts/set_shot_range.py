"""Modify the start/end frame of an existing shot node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def set_shot_range(
    shot_node: str,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    sequence_start_frame: Optional[float] = None,
) -> dict:
    """Update the frame range of an existing shot node.

    Args:
        shot_node: Name of the shot node to modify.
        start_frame: New start time.  If ``None``, the current value is kept.
        end_frame: New end time.  If ``None``, the current value is kept.
        sequence_start_frame: New sequence start position.  If ``None``, kept.

    Returns:
        ActionResultModel dict with the updated ``shot_node``, ``start_frame``,
        ``end_frame``, and ``sequence_start_frame``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(shot_node):
            return error_result(
                "Shot not found: {}".format(shot_node),
                "Verify the shot node name with list_shots",
            ).to_dict()

        current_start = float(cmds.shot(shot_node, query=True, startTime=True))
        current_end = float(cmds.shot(shot_node, query=True, endTime=True))
        current_seq = float(cmds.shot(shot_node, query=True, sequenceStartTime=True))

        new_start = start_frame if start_frame is not None else current_start
        new_end = end_frame if end_frame is not None else current_end
        new_seq = sequence_start_frame if sequence_start_frame is not None else current_seq
        new_seq_end = new_seq + (new_end - new_start)

        cmds.shot(
            shot_node,
            edit=True,
            startTime=new_start,
            endTime=new_end,
            sequenceStartTime=new_seq,
            sequenceEndTime=new_seq_end,
        )

        return success_result(
            "Shot '{}' range updated to [{}-{}]".format(shot_node, new_start, new_end),
            prompt="Use list_shots to review the full sequence order.",
            shot_node=shot_node,
            start_frame=new_start,
            end_frame=new_end,
            sequence_start_frame=new_seq,
            sequence_end_frame=new_seq_end,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_shot_range failed")
        return error_result("Failed to set shot range", str(exc)).to_dict()


def main(**kwargs):
    return set_shot_range(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_shot_range("shot1", start_frame=10, end_frame=60)))
