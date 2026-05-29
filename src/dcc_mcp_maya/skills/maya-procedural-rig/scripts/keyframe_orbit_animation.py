"""Keyframe a procedural orbit / bounce / spin animation (issue #306).

Stage five: set deterministic keyframes on a set of nodes (typically the rig
joints) across a frame range so the playblast stage has motion to capture.
"""

from __future__ import annotations

import math
import random
from typing import List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_MODES = ("orbit", "bounce", "spin")
_AXES = {"x": 0, "y": 1, "z": 2}


def keyframe_orbit_animation(
    nodes: List[str],
    start_frame: int = 1,
    end_frame: int = 120,
    keys: int = 5,
    amplitude: float = 5.0,
    axis: str = "y",
    mode: str = "orbit",
    seed: int = 0,
) -> dict:
    """Set keyframes describing a looping motion on each node.

    Args:
        nodes: Transform/joint names to animate.
        start_frame: First keyframe.
        end_frame: Last keyframe.
        keys: Number of keyframes per node across the range (>=2).
        amplitude: Motion magnitude (translate units or degrees for ``spin``).
        axis: Primary axis ``x`` / ``y`` / ``z``.
        mode: ``orbit`` (circular translate), ``bounce`` (axis translate),
            or ``spin`` (axis rotate).
        seed: Per-node phase offset seed (deterministic).

    Returns:
        ToolResult dict with ``context.keyed_count`` and frame range.
    """
    if mode not in _MODES:
        return maya_error("Invalid mode", "mode must be one of {}".format(", ".join(_MODES)))
    if axis not in _AXES:
        return maya_error("Invalid axis", "axis must be x, y, or z")
    if not nodes:
        return maya_error("No nodes", "nodes must contain at least one name")
    if end_frame <= start_frame:
        return maya_error("Invalid range", "end_frame must be greater than start_frame")
    keys = max(2, int(keys))

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )

    try:
        rng = random.Random(seed)
        span = end_frame - start_frame
        keyed = 0
        for node in nodes:
            if not cmds.objExists(node):
                return maya_error("Node not found", "missing node: {}".format(node))
            base = cmds.xform(node, query=True, worldSpace=False, translation=True)
            phase = rng.random() * math.tau
            for k in range(keys):
                t = k / float(keys - 1)
                frame = start_frame + t * span
                angle = phase + t * math.tau
                if mode == "spin":
                    attr = "r" + axis
                    cmds.setKeyframe(node, attribute=attr, value=amplitude * 360.0 * t, time=frame)
                elif mode == "bounce":
                    attr = "t" + axis
                    value = base[_AXES[axis]] + amplitude * abs(math.sin(angle))
                    cmds.setKeyframe(node, attribute=attr, value=value, time=frame)
                else:  # orbit
                    cmds.setKeyframe(node, attribute="tx", value=base[0] + amplitude * math.cos(angle), time=frame)
                    cmds.setKeyframe(node, attribute="tz", value=base[2] + amplitude * math.sin(angle), time=frame)
                keyed += 1

        cmds.playbackOptions(minTime=start_frame, maxTime=end_frame)
        return maya_success(
            "Keyed {} nodes ({}) from frame {} to {}".format(len(nodes), mode, start_frame, end_frame),
            prompt="Use create_playblast to render a preview of the animation.",
            keyed_count=keyed,
            node_count=len(nodes),
            start_frame=start_frame,
            end_frame=end_frame,
            mode=mode,
        )
    except Exception as exc:  # noqa: BLE001
        return maya_from_exception(exc, message="Failed to keyframe animation")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`keyframe_orbit_animation`."""
    return keyframe_orbit_animation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
