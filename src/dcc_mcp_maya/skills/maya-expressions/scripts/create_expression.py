"""Create a Maya expression node that drives attributes procedurally."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional, Union

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_VALID_UNIT_CONVERSIONS = {"none", "angularOnly", "all"}


def create_expression(
    expression: str,
    name: Optional[str] = None,
    object: Optional[str] = None,
    object_name: Optional[str] = None,
    attribute: Optional[str] = None,
    unit_conversion: Union[str, int, None] = "all",
) -> dict:
    """Create an expression node.

    Args:
        expression: MEL expression string. Must be non-empty and non-whitespace.
        name: Optional name for the expression node.
        object: Optional object to set as 'defaultObject' on the expression
            (alias for ``object_name``).
        object_name: Optional object name used as context and to verify existence.
        attribute: Optional attribute name recorded in context.
        unit_conversion: One of ``"none"``, ``"angularOnly"``, ``"all"``. Default ``"all"``.

    Returns:
        ActionResultModel dict with ``context.expression_name``, ``context.expression_str``,
        and optional ``context.object_name``.
    """
    if not expression or not expression.strip():
        return skill_error("Missing parameter", "'expression' string is required and must not be empty")

    # Validate unit_conversion
    if unit_conversion is not None and not isinstance(unit_conversion, str):
        return skill_error(
            "Invalid parameter",
            "'unit_conversion' must be one of: {}".format(sorted(_VALID_UNIT_CONVERSIONS)),
        )
    if isinstance(unit_conversion, str) and unit_conversion not in _VALID_UNIT_CONVERSIONS:
        return skill_error(
            "Invalid unit_conversion '{}'".format(unit_conversion),
            "Must be one of: {}".format(sorted(_VALID_UNIT_CONVERSIONS)),
        )

    # Normalise object param
    obj = object_name or object or None

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Validate object existence if specified
        if obj and not cmds.objExists(obj):
            return skill_error(
                "Object '{}' not found".format(obj),
                "Ensure the object exists in the scene before creating the expression.",
            )

        kwargs = {"string": expression}
        if unit_conversion:
            kwargs["unitConversion"] = unit_conversion
        if name:
            kwargs["name"] = name
        if obj:
            kwargs["object"] = obj

        node = cmds.expression(**kwargs)

        ctx = {
            "expression_name": node,
            "node": node,
            "expression_str": expression,
        }
        if obj:
            ctx["object_name"] = obj
        if attribute:
            ctx["attribute"] = attribute

        return skill_success(
            "Expression node '{}' created".format(node),
            prompt="Expression is live. Use list_expressions to verify or delete_expression to remove.",
            **ctx,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create expression")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_expression`."""
    return create_expression(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
