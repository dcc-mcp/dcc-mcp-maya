"""Modify the start/end frame of an existing shot node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(shot_node):
            return skill_error(
                "Shot not found: {}".format(shot_node),
                "Verify the shot node name with list_shots",
            )

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

        return skill_success(
            "Shot '{}' range updated to [{}-{}]".format(shot_node, new_start, new_end),
            prompt="Use list_shots to review the full sequence order.",
            shot_node=shot_node,
            start_frame=new_start,
            end_frame=new_end,
            sequence_start_frame=new_seq,
            sequence_end_frame=new_seq_end,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set shot range")


@skill_entry
def main(**kwargs):
    return set_shot_range(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
