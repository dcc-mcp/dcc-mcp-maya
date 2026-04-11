"""Add a pfxToon outline stroke to selected or specified meshes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def add_toon_outline(
    objects: Optional[List[str]] = None,
    line_width: float = 1.0,
    line_color: Optional[List[float]] = None,
    name: str = "pfxToon1",
) -> dict:
    """Add a pfxToon outline stroke to meshes.

    Args:
        objects: Mesh or transform names to receive the outline.  If None,
            the current selection is used.
        line_width: Outline stroke width.  Default: 1.0.
        line_color: RGB color as ``[r, g, b]`` in 0-1 range.  Default: black.
        name: Name for the created pfxToon node.  Default: ``pfxToon1``.

    Returns:
        ActionResultModel dict with the created node name and linked objects.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        targets = objects or (cmds.ls(selection=True) or [])
        if not targets:
            return skill_error(
                "No objects specified",
                "Provide 'objects' or select meshes in Maya",
            )

        # Resolve mesh shapes
        mesh_shapes = []
        for obj in targets:
            if cmds.objectType(obj) == "mesh":
                mesh_shapes.append(obj)
            else:
                shapes = cmds.listRelatives(obj, shapes=True, type="mesh") or []
                mesh_shapes.extend(shapes)

        if not mesh_shapes:
            return skill_error(
                "No mesh shapes found in the specified objects",
                "Ensure the objects are polygon meshes",
            )

        # Select meshes and run toon MEL command
        cmds.select(mesh_shapes, replace=True)
        mel.eval("assignNewPfxToon;")

        # Rename the last created pfxToon
        toon_nodes = cmds.ls(type="pfxToon") or []
        toon_node = toon_nodes[-1] if toon_nodes else "pfxToon1"
        if toon_node != name:
            try:
                toon_node = cmds.rename(toon_node, name)
            except Exception:
                pass

        # Apply style settings
        if cmds.attributeQuery("lineWidth", node=toon_node, exists=True):
            cmds.setAttr("{}.lineWidth".format(toon_node), line_width)

        color = line_color if line_color else [0.0, 0.0, 0.0]
        for i, ch in enumerate(["R", "G", "B"]):
            attr = "lineColor{}".format(ch)
            if cmds.attributeQuery(attr, node=toon_node, exists=True):
                cmds.setAttr("{}.{}".format(toon_node, attr), color[i])

        return skill_success(
            "Added toon outline '{}' to {} mesh(es)".format(toon_node, len(mesh_shapes)),
            prompt="Use set_outline_width to adjust line width or list_toon_outlines to inspect.",
            toon_node=toon_node,
            meshes=mesh_shapes,
            line_width=line_width,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add toon outline")


@skill_entry
def main(**kwargs):
    return add_toon_outline(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
