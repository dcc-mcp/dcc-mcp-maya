"""Delete a Maya fluid container by transform name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_fluid_container(name: str) -> dict:
    """Delete a fluid container transform (and its fluidShape child).

    Args:
        name: Transform node name of the fluid container to delete.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, name)
        if err:
            return err

        cmds.delete(name)

        return skill_success(
            "Fluid container deleted",
            prompt="Container '{}' removed. Use create_fluid_container to add a new one.".format(name),
            deleted=name,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete fluid container")


@skill_entry
def main(**kwargs):
    return delete_fluid_container(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
