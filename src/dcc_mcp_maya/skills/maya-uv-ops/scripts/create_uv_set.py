"""Create a new UV set on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_uv_set(object_name: str, uv_set_name: str, copy_from: Optional[str] = None) -> dict:
    """Create a new UV set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name for the new UV set.
        copy_from: Optional existing UV set name to copy UVs from.

    Returns:
        ActionResultModel dict with ``context.uv_set_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name in existing:
            return skill_error("UV set '{}' already exists on '{}'".format(uv_set_name, object_name))

        if copy_from:
            if copy_from not in existing:
                return skill_error("Source UV set '{}' not found on '{}'".format(copy_from, object_name))
            cmds.polyUVSet(object_name, copy=True, uvSet=copy_from, newUVSet=uv_set_name)
        else:
            cmds.polyUVSet(object_name, create=True, uvSet=uv_set_name)

        return skill_success(
            "Created UV set '{}' on '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
            copied_from=copy_from,
            prompt="Check the result with list_uv_ops or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create UV set")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_uv_set`."""
    return create_uv_set(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
