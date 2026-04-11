"""List all expression nodes in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def list_expressions(
    object: Optional[str] = None,
    object_name: Optional[str] = None,
) -> dict:
    """List expression nodes in the scene.

    Args:
        object: Filter — only return expressions whose string or defaultObject
            contains this value (alias for ``object_name``).
        object_name: Filter by object name. Same behaviour as ``object``.

    Returns:
        ActionResultModel dict with ``context.expressions`` list and ``context.count``.
        Each expression entry has keys ``name``, ``node``, ``expression_str``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    # Normalise filter param
    obj_filter = object_name or object or None

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Validate object existence if filter specified
        if obj_filter and not cmds.objExists(obj_filter):
            return error_result(
                "Object '{}' not found".format(obj_filter),
                "Ensure the object exists in the scene.",
            ).to_dict()

        all_expr = cmds.ls(type="expression") or []
        results = []
        for node in all_expr:
            expr_str = cmds.expression(node, query=True, string=True) or ""
            if obj_filter and obj_filter not in expr_str:
                continue
            default_obj = ""
            try:
                default_obj = cmds.expression(node, query=True, object=True) or ""
            except Exception:
                pass
            results.append(
                {
                    "name": node,
                    "node": node,
                    "expression_str": expr_str,
                    "default_object": default_obj,
                }
            )

        return success_result(
            "Found {} expression node(s)".format(len(results)),
            prompt="Use create_expression to add more or delete_expression to remove unwanted ones.",
            expressions=results,
            count=len(results),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_expressions failed")
        return error_result("Failed to list expressions", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_expressions`."""
    return list_expressions(**kwargs)


if __name__ == "__main__":
    import json

    result = list_expressions()
    print(json.dumps(result))
