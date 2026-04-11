"""Add a Maya constraint from source to target."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes

_CONSTRAINT_TYPES = {
    "parent": "parentConstraint",
    "point": "pointConstraint",
    "orient": "orientConstraint",
    "scale": "scaleConstraint",
    "aim": "aimConstraint",
    "geometry": "geometryConstraint",
    "normal": "normalConstraint",
    "tangent": "tangentConstraint",
}


def add_constraint(
    constraint_type: str,
    source: str,
    target: str,
    maintain_offset: bool = True,
    weight: float = 1.0,
) -> dict:
    """Add a Maya constraint from source to target.

    Args:
        constraint_type: One of ``parent``, ``point``, ``orient``, ``scale``,
            ``aim``, ``geometry``, ``normal``, ``tangent``.
        source: Name of the driver (source) object.
        target: Name of the driven (target) object.
        maintain_offset: Preserve the current offset between source and target.
        weight: Initial constraint weight.  Default 1.0.

    Returns:
        ActionResultModel dict with ``context.constraint_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if constraint_type not in _CONSTRAINT_TYPES:
            return skill_error(
                "Unknown constraint type: {}".format(constraint_type),
                "Supported types: {}".format(", ".join(sorted(_CONSTRAINT_TYPES))),
            )

        err = batch_validate_nodes(cmds, [source, target])
        if err:
            return err

        cmd_fn = getattr(cmds, _CONSTRAINT_TYPES[constraint_type])
        result = cmd_fn(source, target, maintainOffset=maintain_offset, weight=weight)
        constraint_node = result[0] if result else ""

        return skill_success(
            "Added {} constraint '{}' → '{}'".format(constraint_type, source, target),
            prompt="Use list_constraints to see all constraints on the target, or remove_constraint to remove it.",
            constraint_node=constraint_node,
            constraint_type=constraint_type,
            source=source,
            target=target,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add constraint")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_constraint`."""
    return add_constraint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
