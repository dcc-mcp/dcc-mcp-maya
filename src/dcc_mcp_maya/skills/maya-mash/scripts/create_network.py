"""Create a MASH network for an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_network(
    object_name: str,
    network_name: str = "",
    geometry_type: str = "Instancer",
) -> dict:
    """Create a MASH network for an object.

    Args:
        object_name: Object to use as the MASH instancer source.
        network_name: Name for the MASH network. Auto-generated if omitted.
        geometry_type: "Instancer" (default) or "Repro".

    Returns:
        ToolResult dict with ``context.network_name``, ``context.instancer``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        import MASH.api as mapi  # noqa: PLC0415

        mash = mapi.Network()
        if network_name:
            mash.createNetwork(object_name, networkName=network_name, geometryType=geometry_type)
        else:
            mash.createNetwork(object_name, geometryType=geometry_type)

        return skill_success(
            "Created MASH network for '{}'".format(object_name),
            prompt="Use add_node to add MASH nodes like Distribute, Random, or Dynamics.",
            network_name=mash.meshName,
            instancer=mash.instancer,
            waiter=mash.waiter,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to create MASH network",
            prompt="Ensure MASH plugin is loaded: cmds.loadPlugin('MASH').",
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_network`."""
    return create_network(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
