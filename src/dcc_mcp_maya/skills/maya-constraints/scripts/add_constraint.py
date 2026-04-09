"""Add a Maya constraint from source to target."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if constraint_type not in _CONSTRAINT_TYPES:
            return error_result(
                "Unknown constraint type: {}".format(constraint_type),
                "Supported types: {}".format(", ".join(sorted(_CONSTRAINT_TYPES))),
            ).to_dict()

        for obj in (source, target):
            if not cmds.objExists(obj):
                return error_result(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist".format(obj),
                ).to_dict()

        cmd_fn = getattr(cmds, _CONSTRAINT_TYPES[constraint_type])
        result = cmd_fn(source, target, maintainOffset=maintain_offset, weight=weight)
        constraint_node = result[0] if result else ""

        return success_result(
            "Added {} constraint '{}' → '{}'".format(constraint_type, source, target),
            prompt="Use list_constraints to see all constraints on the target, or remove_constraint to remove it.",
            constraint_node=constraint_node,
            constraint_type=constraint_type,
            source=source,
            target=target,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_constraint failed")
        return error_result("Failed to add constraint", str(exc)).to_dict()


def main(**kwargs):
    return add_constraint(**kwargs)


if __name__ == "__main__":
    import json

    result = add_constraint("parent", "pSphere1", "pCube1")
    print(json.dumps(result))
