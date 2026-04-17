"""Delete a UV set from a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def delete_uv_set(object_name: str, uv_set_name: str) -> dict:
    """Delete a UV set from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name of the UV set to delete.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name not in existing:
            return skill_error(
                "UV set '{}' not found on '{}'".format(uv_set_name, object_name),
                "Available UV sets: {}".format(existing),
            )

        # Protect the only remaining UV set
        if len(existing) <= 1:
            return skill_error(
                "Cannot delete the only UV set on '{}'".format(object_name), "A mesh must have at least one UV set"
            )

        cmds.polyUVSet(object_name, delete=True, uvSet=uv_set_name)

        return skill_success(
            "Deleted UV set '{}' from '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
            prompt="Check the result with list_uv_ops or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete UV set")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_uv_set`."""
    return delete_uv_set(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
