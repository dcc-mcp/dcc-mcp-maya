"""Create an XGen description on a mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_description(
    mesh: str,
    collection: str = "xgenCollection1",
    description: str = "description1",
    primitive: str = "SplinePrimitive",
) -> dict:
    """Create an XGen description (hair/fur) on a bound mesh.

    Args:
        mesh: The mesh transform to bind XGen to.
        collection: XGen collection name. Defaults to "xgenCollection1".
        description: Description name. Defaults to "description1".
        primitive: Primitive type: "SplinePrimitive" (default), "CardPrimitive",
            "SpherePrimitive".

    Returns:
        ActionResultModel dict with ``context.collection``, ``context.description``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        import xgenm as xg  # noqa: PLC0415

        palette = xg.createPalette(collection)
        desc = xg.createDescription(palette, description, primitive, mesh)
        return skill_success(
            "Created XGen description '{}' on '{}'".format(desc, mesh),
            prompt="Use set_xgen_attribute to configure density, length, and other parameters.",
            collection=palette,
            description=desc,
            mesh=mesh,
            primitive=primitive,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to create XGen description",
            prompt="Ensure XGen plugin is loaded: cmds.loadPlugin('xgenToolkit').",
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_description`."""
    return create_description(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
