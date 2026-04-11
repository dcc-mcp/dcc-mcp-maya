"""Bake constraint-driven animation to explicit keyframes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = list(objects) if objects else []
        if targets:
            missing = [o for o in targets if not cmds.objExists(o)]
            if missing:
                return skill_error(
                    "Objects not found: {}".format(", ".join(missing)),
                    "The following objects do not exist: {}".format(", ".join(missing)),
                )
            cmds.select(targets, replace=True)
        else:
            targets = cmds.ls(selection=True) or []

        if not targets:
            return skill_error(
                "No objects to bake",
                "Provide object names or select objects before baking",
            )

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

        return skill_success(
            "Baked constraints on {} object(s) from frame {} to {}".format(len(targets), start_frame, end_frame),
            object_count=len(targets),
            objects=targets,
            start_frame=start_frame,
            end_frame=end_frame,
            sample_by=sample_by,
            removed_constraints=removed_constraints,
            prompt="Use list_animation_curves or set_keyframe to adjust the baked keys.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake constraints")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_constraints`."""
    return bake_constraints(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
