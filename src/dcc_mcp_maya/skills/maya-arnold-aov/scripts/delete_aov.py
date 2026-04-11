"""Delete an Arnold AOV node by name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_aov(name: str) -> dict:
    """Delete the Arnold AOV node whose ``name`` attribute matches *name*.

    Args:
        name: The AOV name as set in the ``aiAOV.name`` attribute (not the
            Maya node name).

    Returns:
        ActionResultModel dict with ``context.deleted_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return error_result("AOV name is required", "Provide a non-empty AOV name").to_dict()

        nodes = cmds.ls(type="aiAOV") or []
        target_node = None
        for node in nodes:
            try:
                if cmds.getAttr("{}.name".format(node)) == name:
                    target_node = node
                    break
            except Exception:
                pass

        if target_node is None:
            return error_result(
                "AOV '{}' not found".format(name),
                "No aiAOV node with name '{}' exists in the scene".format(name),
            ).to_dict()

        cmds.delete(target_node)
        return success_result(
            "Deleted Arnold AOV '{}'".format(name),
            prompt="Use list_aovs to verify the AOV was removed.",
            deleted_node=target_node,
            aov_name=name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_aov failed")
        return error_result("Failed to delete AOV '{}'".format(name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_aov`."""
    return delete_aov(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_aov("diffuse")
    print(json.dumps(result))
