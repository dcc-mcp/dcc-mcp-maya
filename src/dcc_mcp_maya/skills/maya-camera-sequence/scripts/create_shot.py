"""Create a Maya shot node and assign a camera for a frame range."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_shot(
    camera: str,
    start_frame: float = 1.0,
    end_frame: float = 24.0,
    name: str = "",
    sequence_start_frame: Optional[float] = None,
) -> dict:
    """Create a shot node in the Maya camera sequencer.

    Args:
        camera: Name of the camera transform to assign to the shot.
        start_frame: First frame of the shot.  Default: ``1.0``.
        end_frame: Last frame of the shot.  Default: ``24.0``.
        name: Name for the new shot node.  If empty, Maya assigns one.
        sequence_start_frame: Where the shot sits in the overall sequence.
            Defaults to ``start_frame``.

    Returns:
        ActionResultModel dict with ``shot_node``, ``camera``, ``start_frame``,
        ``end_frame``, and ``sequence_start_frame``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera):
            return error_result(
                "Camera not found: {}".format(camera),
                "Create the camera first or verify its name",
            ).to_dict()

        seq_start = sequence_start_frame if sequence_start_frame is not None else start_frame

        shot_kwargs = {
            "startTime": start_frame,
            "endTime": end_frame,
            "sequenceStartTime": seq_start,
            "sequenceEndTime": seq_start + (end_frame - start_frame),
            "currentCamera": camera,
        }
        if name:
            shot_kwargs["name"] = name

        shot_node = cmds.shot(**shot_kwargs)

        return success_result(
            "Created shot '{}' for camera '{}' [{}-{}]".format(shot_node, camera, start_frame, end_frame),
            prompt="Use list_shots to view sequence order or set_shot_range to adjust timing.",
            shot_node=shot_node,
            camera=camera,
            start_frame=start_frame,
            end_frame=end_frame,
            sequence_start_frame=seq_start,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_shot failed")
        return error_result("Failed to create shot", str(exc)).to_dict()


def main(**kwargs):
    return create_shot(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_shot("camera1", 1, 48)))
