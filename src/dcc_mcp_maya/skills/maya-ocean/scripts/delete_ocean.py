"""Delete a Maya oceanShader node and its connected geometry."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_ocean(name: str, delete_geometry: bool = False) -> dict:
    """Delete an oceanShader node and optionally its connected plane geometry.

    Args:
        name: Name of the oceanShader node to delete.
        delete_geometry: If True, also delete any connected mesh transforms.

    Returns:
        ActionResultModel dict indicating success or failure.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result("Missing required parameter 'name'", "Provide the oceanShader node name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Ocean shader '{}' not found".format(name),
                "Use list_oceans to find valid ocean names.",
            ).to_dict()

        node_type = cmds.objectType(name)
        if node_type != "oceanShader":
            return error_result(
                "Node '{}' is not an oceanShader (got '{}')".format(name, node_type),
                "Provide an oceanShader node name.",
            ).to_dict()

        deleted = [name]

        if delete_geometry:
            # Find shading groups connected to this shader
            sgs = cmds.listConnections("{}.outColor".format(name), type="shadingEngine") or []
            for sg in sgs:
                members = cmds.sets(sg, query=True) or []
                for member in members:
                    transform = cmds.listRelatives(member, parent=True, fullPath=False)
                    node_to_del = transform[0] if transform else member
                    if cmds.objExists(node_to_del):
                        cmds.delete(node_to_del)
                        deleted.append(node_to_del)
                if cmds.objExists(sg):
                    cmds.delete(sg)
                    deleted.append(sg)

        cmds.delete(name)

        return success_result(
            "Deleted ocean shader '{}'".format(name),
            prompt="Ocean deleted. Use create_ocean to create a new one.",
            deleted=deleted,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_ocean failed")
        return error_result("Failed to delete ocean", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_ocean(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_ocean(name="ocean_shader")))
