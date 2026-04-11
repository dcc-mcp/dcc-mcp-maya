"""Delete a Maya fluid container by transform name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def delete_fluid_container(name: str) -> dict:
    """Delete a fluid container transform (and its fluidShape child).

    Args:
        name: Transform node name of the fluid container to delete.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return maya_error(
                "Node not found",
                "Fluid container '{}' does not exist".format(name),
            )

        cmds.delete(name)

        return maya_success(
            "Fluid container deleted",
            prompt="Container '{}' removed. Use create_fluid_container to add a new one.".format(name),
            deleted=name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete fluid container")


def main(**kwargs):
    return delete_fluid_container(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_fluid_container("fluid1")
    print(json.dumps(result))
