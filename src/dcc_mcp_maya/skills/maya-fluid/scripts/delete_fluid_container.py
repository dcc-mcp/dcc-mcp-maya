"""Delete a Maya Fluid container and optionally its emitters."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_fluid_container(fluid_node: str, delete_emitters: bool = True) -> dict:
    """Delete a Maya Fluid Effects container.

    Args:
        fluid_node: Name of the fluidShape or its parent transform.
        delete_emitters: If ``True``, also delete any connected fluid emitters.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not fluid_node:
        return error_result("No fluid node specified", "Provide a fluidShape or transform name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(fluid_node):
            return error_result(
                "Fluid node '{}' does not exist".format(fluid_node),
                "Check the node name with list_fluid_containers.",
            ).to_dict()

        node_type = cmds.objectType(fluid_node)
        if node_type == "fluidShape":
            shape = fluid_node
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            target = parents[0] if parents else shape
        else:
            target = fluid_node
            shapes = cmds.listRelatives(target, shapes=True, type="fluidShape") or []
            shape = shapes[0] if shapes else None

        deleted_emitters = []
        if delete_emitters and shape:
            emitters = cmds.listConnections(shape, type="fluidEmitter") or []
            for em in set(emitters):
                if cmds.objExists(em):
                    em_parents = cmds.listRelatives(em, parent=True, fullPath=False) or []
                    em_target = em_parents[0] if em_parents else em
                    cmds.delete(em_target)
                    deleted_emitters.append(em)

        cmds.delete(target)

        return success_result(
            "Deleted fluid container '{}'{}".format(
                fluid_node,
                " and {} emitter(s)".format(len(deleted_emitters)) if deleted_emitters else "",
            ),
            prompt="Fluid container deleted. Use create_fluid_container to add a new one.",
            deleted_node=fluid_node,
            deleted_emitters=deleted_emitters,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_fluid_container failed")
        return error_result("Failed to delete fluid container", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_fluid_container(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_fluid_container("fluidShape1")))
