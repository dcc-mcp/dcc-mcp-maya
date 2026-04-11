"""Create a blend shape deformer on a base mesh with one or more target meshes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_blend_shape(
    base_mesh: str,
    targets: List[str],
    name: Optional[str] = None,
    origin: str = "local",
) -> dict:
    """Create a blend shape deformer on the base mesh.

    Each target mesh becomes a blend shape target whose weight can be animated
    between 0.0 (base shape) and 1.0 (full target shape).

    Args:
        base_mesh: Name of the mesh to deform (must exist in the scene).
        targets: List of target mesh names.  Each must be a mesh that shares
            the same topology as *base_mesh*.
        name: Optional name for the blendShape node.  Defaults to Maya's
            automatic naming (e.g. ``blendShape1``).
        origin: Deformer origin mode — ``"local"`` (default) or ``"world"``.

    Returns:
        ActionResultModel dict with ``context.blend_shape_node`` and
        ``context.targets``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(base_mesh):
            return error_result(
                "Base mesh not found: {}".format(base_mesh),
                "'{}' does not exist in the scene".format(base_mesh),
            ).to_dict()

        missing = [t for t in targets if not cmds.objExists(t)]
        if missing:
            return error_result(
                "Target meshes not found",
                "Missing: {}".format(", ".join(missing)),
            ).to_dict()

        kwargs = {"origin": origin}
        if name:
            kwargs["name"] = name

        # blendShape([targets...], baseMesh)
        node = cmds.blendShape(targets + [base_mesh], **kwargs)
        node_name = node[0] if isinstance(node, list) else node

        return success_result(
            "Created blend shape '{}' on '{}' with {} target(s)".format(node_name, base_mesh, len(targets)),
            prompt=(
                "Use set_blend_shape_weight to drive target weights, "
                "or get_blend_shape_weights to inspect current values."
            ),
            blend_shape_node=node_name,
            base_mesh=base_mesh,
            targets=targets,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_blend_shape failed")
        return error_result("Failed to create blend shape", str(exc)).to_dict()


def main(**kwargs):
    return create_blend_shape(**kwargs)


if __name__ == "__main__":
    import json

    result = create_blend_shape("pSphere1", ["pSphere2"], name="testBS")
    print(json.dumps(result, indent=2))
