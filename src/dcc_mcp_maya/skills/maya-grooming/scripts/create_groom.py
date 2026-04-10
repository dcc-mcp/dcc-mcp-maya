"""Create an XGen interactive groom description on a mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_groom(
    mesh: str,
    name: Optional[str] = None,
    description_type: str = "hair",
) -> dict:
    """Create an XGen interactive groom description attached to a mesh.

    Args:
        mesh: Name of the Maya mesh (transform or shape node).
        name: Optional name for the groom description node.
        description_type: Groom type — ``hair``, ``fur``, or ``feathers``.

    Returns:
        ActionResultModel dict with ``context.groom_node`` and ``context.mesh``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not mesh:
        return error_result("No mesh specified", "Provide a valid mesh name.").to_dict()

    valid_types = ("hair", "fur", "feathers")
    if description_type not in valid_types:
        return error_result(
            "Invalid description_type '{}'".format(description_type),
            "Supported types: {}".format(", ".join(valid_types)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh '{}' does not exist".format(mesh),
                "Check the object name and try again.",
            ).to_dict()

        # Load the XGen plugin if not already loaded
        if not cmds.pluginInfo("xgenToolkit", query=True, loaded=True):
            cmds.loadPlugin("xgenToolkit", quiet=True)

        create_kwargs = {"mesh": mesh, "groomType": description_type}
        if name:
            create_kwargs["name"] = name

        groom_node = cmds.igCreateGroom(**create_kwargs)

        return success_result(
            "Created groom '{}' on mesh '{}'".format(groom_node, mesh),
            prompt=(
                "Groom created. Use convert_groom_to_curves to extract curves, "
                "or export_groom_cache to save the groom to disk."
            ),
            groom_node=groom_node,
            mesh=mesh,
            description_type=description_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_groom failed")
        return error_result("Failed to create groom", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_groom(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_groom("pSphere1")))
