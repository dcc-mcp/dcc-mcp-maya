"""Maya expression actions.

Provides helpers to create, list, and delete Maya expression nodes.
Expressions are small MEL snippets evaluated each frame to drive attribute
values procedurally without keyframes.
"""

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


def list_expressions(
    object_name: Optional[str] = None,
) -> dict:
    """List Maya expression nodes in the scene.

    Args:
        object_name: If specified, only return expressions that reference
            this node.  If None, all expression nodes are returned.

    Returns:
        ActionResultModel dict with ``context.expressions`` — a list of
        dicts with ``name`` and ``string`` (the MEL expression body), and
        ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if object_name and not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        all_exprs = cmds.ls(type="expression") or []

        if object_name:
            filtered = []
            for expr in all_exprs:
                expr_str = cmds.expression(expr, query=True, string=True) or ""
                if object_name in expr_str:
                    filtered.append(expr)
            all_exprs = filtered

        expressions = []
        for expr in all_exprs:
            try:
                expr_str = cmds.expression(expr, query=True, string=True) or ""
            except Exception:
                expr_str = ""
            expressions.append({"name": expr, "string": expr_str})

        return success_result(
            "Found {} expression(s){}".format(
                len(expressions),
                " on '{}'".format(object_name) if object_name else "",
            ),
            expressions=expressions,
            count=len(expressions),
            object_name=object_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_expressions failed")
        return error_result("Failed to list expressions", str(exc)).to_dict()


def delete_expression(
    expression_name: str,
) -> dict:
    """Delete a Maya expression node by name.

    Args:
        expression_name: Name of the expression node to delete.

    Returns:
        ActionResultModel dict with ``context.expression_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(expression_name):
            return error_result(
                "Expression not found: {}".format(expression_name),
                "'{}' does not exist in the scene".format(expression_name),
            ).to_dict()

        node_type = cmds.objectType(expression_name)
        if node_type != "expression":
            return error_result(
                "Not an expression node: {}".format(expression_name),
                "'{}' is of type '{}', expected 'expression'".format(expression_name, node_type),
            ).to_dict()

        cmds.delete(expression_name)

        return success_result(
            "Deleted expression '{}'".format(expression_name),
            expression_name=expression_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_expression failed")
        return error_result("Failed to delete expression {}".format(expression_name), str(exc)).to_dict()
