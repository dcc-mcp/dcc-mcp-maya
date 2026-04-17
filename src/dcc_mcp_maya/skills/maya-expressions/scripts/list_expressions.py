"""List all expression nodes in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
        ToolResult dict with ``context.expressions`` list and ``context.count``.
        Each expression entry has keys ``name``, ``node``, ``expression_str``.
    """
    # Normalise filter param
    obj_filter = object_name or object or None

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Validate object existence if filter specified
        if obj_filter and not cmds.objExists(obj_filter):
            return skill_error(
                "Object '{}' not found".format(obj_filter),
                "Ensure the object exists in the scene.",
            )

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

        return skill_success(
            "Found {} expression node(s)".format(len(results)),
            prompt="Use create_expression to add more or delete_expression to remove unwanted ones.",
            expressions=results,
            count=len(results),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list expressions")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_expressions`."""
    return list_expressions(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
