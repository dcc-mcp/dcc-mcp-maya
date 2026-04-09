"""Add a Maya constraint from source to target."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def add_constraint(
    source: str,
    target: str,
    constraint_type: str = "parent",
    maintain_offset: bool = True,
    name: Optional[str] = None,
) -> dict:
    """Add a Maya constraint from *source* to *target*.

    Supported constraint types: ``"parent"``, ``"point"``, ``"orient"``,
    ``"scale"``, ``"aim"``.

    Args:
        source: Name of the driver object (constrains *target* to follow this).
        target: Name of the object to be constrained.
        constraint_type: One of ``"parent"``, ``"point"``, ``"orient"``,
            ``"scale"``, ``"aim"``.  Default: ``"parent"``.
        maintain_offset: If True, preserve the current offset between the
            objects.  Default: True.
        name: Optional name for the constraint node.

    Returns:
        ActionResultModel dict with ``context.constraint_name``,
        ``context.constraint_type``, ``context.source``, ``context.target``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_TYPES = ("parent", "point", "orient", "scale", "aim")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source):
            return error_result(
                "Source not found: {}".format(source),
                "'{}' does not exist in the scene".format(source),
            ).to_dict()

        if not cmds.objExists(target):
            return error_result(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            ).to_dict()

        if constraint_type not in _VALID_TYPES:
            return error_result(
                "Invalid constraint type: {}".format(constraint_type),
                "constraint_type must be one of {}".format(_VALID_TYPES),
            ).to_dict()

        kwargs = {"maintainOffset": maintain_offset}
        if name:
            kwargs["name"] = name

        _CONSTRAINT_CMDS = {
            "parent": cmds.parentConstraint,
            "point": cmds.pointConstraint,
            "orient": cmds.orientConstraint,
            "scale": cmds.scaleConstraint,
            "aim": cmds.aimConstraint,
        }
        fn = _CONSTRAINT_CMDS[constraint_type]
        result = fn(source, target, **kwargs)
        constraint_name = result[0] if result else (name or "{}_{}1".format(target, constraint_type))

        return success_result(
            "Added {} constraint: '{}' -> '{}'".format(constraint_type, source, target),
            constraint_name=constraint_name,
            constraint_type=constraint_type,
            source=source,
            target=target,
            maintain_offset=maintain_offset,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_constraint failed")
        return error_result("Failed to add {} constraint".format(constraint_type), str(exc)).to_dict()



def main(**kwargs):
    return add_constraint(**kwargs)


if __name__ == "__main__":
    import json
    result = add_constraint()
    print(json.dumps(result))
