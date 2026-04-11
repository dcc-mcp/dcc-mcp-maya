"""List all blend shape nodes in the scene or on a specific mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def list_blend_shapes(mesh: Optional[str] = None) -> dict:
    """List blend shape nodes in the current scene.

    Args:
        mesh: If provided, return only blend shape nodes that deform this mesh.
            If ``None``, all ``blendShape`` nodes in the scene are returned.

    Returns:
        ActionResultModel dict with ``context.blend_shapes`` (list of dicts with
        ``node``, ``base_mesh``, and ``target_count`` keys) and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if mesh:
            err = validate_node_exists(cmds, mesh)
            if err:
                return err
            nodes = cmds.listHistory(mesh, type="blendShape") or []
        else:
            nodes = cmds.ls(type="blendShape") or []

        results = []
        for node in nodes:
            # getAttr returns the number of targets via weight attribute count
            try:
                weights = cmds.blendShape(node, query=True, weight=True) or []
                target_count = len(weights)
            except Exception:
                target_count = 0

            # Identify the base geometry
            base_geos = cmds.blendShape(node, query=True, geometry=True) or []
            base_mesh = base_geos[0] if base_geos else ""

            results.append(
                {
                    "node": node,
                    "base_mesh": base_mesh,
                    "target_count": target_count,
                }
            )

        return skill_success(
            "Found {} blend shape node(s)".format(len(results)),
            prompt=("Use get_blend_shape_weights to inspect targets, or set_blend_shape_weight to animate them."),
            blend_shapes=results,
            count=len(results),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list blend shapes")


@skill_entry
def main(**kwargs):
    return list_blend_shapes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
