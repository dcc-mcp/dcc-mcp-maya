"""List Maya expression nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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


def main(**kwargs):
    return list_expressions(**kwargs)


if __name__ == "__main__":
    import json

    result = list_expressions()
    print(json.dumps(result))
