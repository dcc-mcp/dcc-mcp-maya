"""Delete a light from the scene by transform name."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Supported Maya light types and their corresponding command/node names
_LIGHT_TYPE_MAP = {
    "point": "pointLight",
    "spot": "spotLight",
    "directional": "directionalLight",
    "area": "areaLight",
    "ambient": "ambientLight",
}


def delete_light(light_name: str) -> dict:
    """Delete a light from the scene by transform name.

    Args:
        light_name: Name of the light transform to delete.

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, light_name)
        if err:
            return err

        node_type = cmds.objectType(light_name)
        # If it's a shape, delete its transform
        if node_type not in ("transform",):
            parents = cmds.listRelatives(light_name, parent=True)
            if parents:
                light_name = parents[0]

        cmds.delete(light_name)
        return skill_success(
            "Deleted light '{}'".format(light_name),
            light_name=light_name,
            prompt="Use list_lights to confirm deletion.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete light")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_light`."""
    return delete_light(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
