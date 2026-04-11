"""Delete a Maya fluid container by transform name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_fluid_container(name: str) -> dict:
    """Delete a fluid container transform (and its fluidShape child).

    Args:
        name: Transform node name of the fluid container to delete.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Node not found",
                "Fluid container '{}' does not exist".format(name),
            ).to_dict()

        cmds.delete(name)

        return success_result(
            "Fluid container deleted",
            prompt="Container '{}' removed. Use create_fluid_container to add a new one.".format(name),
            deleted=name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_fluid_container failed")
        return error_result("Failed to delete fluid container", str(exc)).to_dict()


def main(**kwargs):
    return delete_fluid_container(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_fluid_container("fluid1")
    print(json.dumps(result))
