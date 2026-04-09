"""Create a Maya expression node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_expression(
    expression: str,
    name: Optional[str] = None,
    object_name: Optional[str] = None,
    attribute: Optional[str] = None,
    unit_conversion: int = 0,
) -> dict:
    """Create a Maya expression node.

    Expressions are MEL code snippets that Maya evaluates every frame (or on
    demand) to drive attribute values.  Common use cases include procedural
    animation, automated rigging logic, and shader driving.

    Args:
        expression: The MEL expression string.  Example:
            ``"pSphere1.translateX = sin(time * 2.0);"``
        name: Optional name for the expression node.  Maya auto-generates
            a name (``"expression1"``) if not specified.
        object_name: Optional name of the Maya node to associate the
            expression with.  When omitted Maya infers the target from the
            expression body.
        attribute: Optional attribute of *object_name* to associate the
            expression with.  Ignored when *object_name* is None.
        unit_conversion: Unit-conversion setting passed to
            ``cmds.expression(unitConversion=…)``.  ``0`` = none,
            ``1`` = all,  ``2`` = angularOnly.  Default: 0.

    Returns:
        ActionResultModel dict with ``context.expression_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_UNIT_CONVERSIONS = (0, 1, 2)

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not expression or not expression.strip():
            return error_result(
                "Empty expression",
                "expression string must not be empty",
            ).to_dict()

        if unit_conversion not in _VALID_UNIT_CONVERSIONS:
            return error_result(
                "Invalid unitConversion value: {}".format(unit_conversion),
                "unitConversion must be one of {}".format(_VALID_UNIT_CONVERSIONS),
            ).to_dict()

        kwargs = {
            "string": expression,
            "unitConversion": unit_conversion,
            "alwaysEvaluate": True,
        }  # type: dict

        if name:
            kwargs["name"] = name
        if object_name:
            if not cmds.objExists(object_name):
                return error_result(
                    "Object not found: {}".format(object_name),
                    "'{}' does not exist in the scene".format(object_name),
                ).to_dict()
            kwargs["object"] = object_name
            if attribute:
                kwargs["attribute"] = attribute

        expr_name = cmds.expression(**kwargs)

        return success_result(
            "Created expression '{}'".format(expr_name),
            expression_name=expr_name,
            object_name=object_name,
            attribute=attribute,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_expression failed")
        return error_result("Failed to create expression", str(exc)).to_dict()


def main(**kwargs):
    return create_expression(**kwargs)


if __name__ == "__main__":
    import json

    result = create_expression()
    print(json.dumps(result))
