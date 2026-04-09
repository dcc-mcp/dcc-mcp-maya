"""Bake constraint-driven animation to explicit keyframes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def bake_constraints(
    objects: Optional[List[str]] = None,
    start_frame: float = 1.0,
    end_frame: float = 120.0,
    sample_by: float = 1.0,
    remove_constraints: bool = False,
) -> dict:
    """Bake constraint-driven animation to explicit keyframes.

    Evaluates constraint outputs every *sample_by* frames over the given
    range and writes the resulting world-space transforms as keyframes.
    After baking the constraints can optionally be deleted.

    Args:
        objects: List of constrained transforms to bake.  Uses the current
            selection when None.
        start_frame: Start of the bake range.  Default: 1.
        end_frame: End of the bake range.  Default: 120.
        sample_by: Sampling interval in frames.  Default: 1.
        remove_constraints: If True, delete all constraints from the baked
            objects after baking.  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_count``,
        ``context.objects``, ``context.removed_constraints``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = list(objects) if objects else []
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
            simulation=False,
            preserveOutsideKeys=True,
            disableImplicitControl=True,
            smart=False,
        )

        removed_constraints = []  # type: List[str]
        if remove_constraints:
            constraint_types = (
                "parentConstraint",
                "pointConstraint",
                "orientConstraint",
                "scaleConstraint",
                "aimConstraint",
                "geometryConstraint",
            )
            for obj in targets:
                for ctype in constraint_types:
                    constraint_nodes = cmds.listRelatives(obj, children=True, type=ctype) or []
                    for node in constraint_nodes:
                        cmds.delete(node)
                        removed_constraints.append(node)

        return success_result(
            "Baked constraints on {} object(s) from frame {} to {}".format(len(targets), start_frame, end_frame),
            object_count=len(targets),
            objects=targets,
            start_frame=start_frame,
            end_frame=end_frame,
            sample_by=sample_by,
            removed_constraints=removed_constraints,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("bake_constraints failed")
        return error_result("Failed to bake constraints", str(exc)).to_dict()


def main(**kwargs):
    return bake_constraints(**kwargs)


if __name__ == "__main__":
    import json

    result = bake_constraints()
    print(json.dumps(result))
