"""List all shot nodes with camera, frame range, and sequence order."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_shots() -> dict:
    """List all shot nodes in the Maya camera sequencer.

    Returns:
        ActionResultModel dict with ``shots`` list sorted by sequence_start_frame.
        Each entry: ``shot_node``, ``camera``, ``start_frame``, ``end_frame``,
        ``sequence_start_frame``, ``sequence_end_frame``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        shot_nodes = cmds.ls(type="shot") or []
        shots = []
        for sn in shot_nodes:
            info = {
                "shot_node": sn,
                "camera": "",
                "start_frame": 0.0,
                "end_frame": 0.0,
                "sequence_start_frame": 0.0,
                "sequence_end_frame": 0.0,
            }
            try:
                info["camera"] = cmds.shot(sn, query=True, currentCamera=True) or ""
            except Exception:
                pass
            try:
                info["start_frame"] = float(cmds.shot(sn, query=True, startTime=True))
            except Exception:
                pass
            try:
                info["end_frame"] = float(cmds.shot(sn, query=True, endTime=True))
            except Exception:
                pass
            try:
                info["sequence_start_frame"] = float(cmds.shot(sn, query=True, sequenceStartTime=True))
            except Exception:
                pass
            try:
                info["sequence_end_frame"] = float(cmds.shot(sn, query=True, sequenceEndTime=True))
            except Exception:
                pass
            shots.append(info)

        shots.sort(key=lambda s: s["sequence_start_frame"])

        return success_result(
            "Found {} shot(s)".format(len(shots)),
            prompt="Use set_shot_range to adjust timing or create_shot to add more shots.",
            shots=shots,
            count=len(shots),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_shots failed")
        return error_result("Failed to list shots", str(exc)).to_dict()


def main(**kwargs):
    return list_shots(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_shots()))
