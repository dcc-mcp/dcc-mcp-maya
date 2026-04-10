"""Delete a Maya pfxToon outline node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_toon_line(name: str) -> dict:
    """Delete a pfxToon outline node by name.

    Args:
        name: Name of the pfxToon node to delete.

    Returns:
        ActionResultModel dict indicating success or failure.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result(
            "Missing required parameter 'name'",
            "Provide the pfxToon node name.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "pfxToon node '{}' not found".format(name),
                "Use list_toon_lines to find valid toon node names.",
            ).to_dict()

        node_type = cmds.objectType(name)
        if node_type != "pfxToon":
            return error_result(
                "Node '{}' is not a pfxToon (got '{}')".format(name, node_type),
                "Provide a pfxToon node name.",
            ).to_dict()

        cmds.delete(name)

        return success_result(
            "Deleted toon line '{}'".format(name),
            prompt="Toon outline deleted. Use create_toon_outline to add a new one.",
            deleted=name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_toon_line failed")
        return error_result("Failed to delete toon line", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_toon_line(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_toon_line(name="pfxToon1")))
