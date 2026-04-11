"""Bake simulation / constraints to keyframes on objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def bake_simulation(
    objects: Optional[List[str]] = None,
    start_frame: float = 1.0,
    end_frame: float = 120.0,
    sample_by: float = 1.0,
) -> dict:
    """Bake simulation / constraints to keyframes on objects.

    Converts dynamic simulation or constraint-driven animation into explicit
    keyframes so the objects can be used independently of the rig.

    Args:
        objects: List of object names to bake.  If None, the current selection
            is used.
        start_frame: First frame of the bake range.  Default: 1.
        end_frame: Last frame of the bake range.  Default: 120.
        sample_by: Baking interval in frames (e.g. ``1.0`` = every frame,
            ``0.5`` = every half-frame).  Default: 1.

    Returns:
        ActionResultModel dict with ``context.object_count`` and frame range.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or []
        if targets:
            missing = [o for o in targets if not cmds.objExists(o)]
            if missing:
                return error_result(
                    "Objects not found: {}".format(", ".join(missing)),
                    "The following objects do not exist: {}".format(", ".join(missing)),
                ).to_dict()
            cmds.select(targets, replace=True)
        else:
            targets = cmds.ls(selection=True) or []

        if not targets:
            return error_result(
                "No objects to bake",
                "Provide object names or select objects before baking",
            ).to_dict()

        cmds.bakeSimulation(
            targets,
            time=(start_frame, end_frame),
            sampleBy=sample_by,
            simulation=True,
            preserveOutsideKeys=True,
        )
        return success_result(
            "Baked {} object(s) from frame {} to {}".format(len(targets), start_frame, end_frame),
            object_count=len(targets),
            objects=targets,
            start_frame=start_frame,
            end_frame=end_frame,
            sample_by=sample_by,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("bake_simulation failed")
        return error_result("Failed to bake simulation", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_simulation`."""
    return bake_simulation(**kwargs)


if __name__ == "__main__":
    import json

    result = bake_simulation()
    print(json.dumps(result))
