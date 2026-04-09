"""Query which shader is assigned to an object or face set."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def get_shader_assignment(object_name: str) -> dict:
    """Query which shader (material) is assigned to an object or face set.

    Args:
        object_name: Transform or mesh node name, or a face component
            (e.g. ``"pCube1"`` or ``"pCube1.f[0:5]"``).

    Returns:
        ActionResultModel dict with ``context.shading_groups`` — a list of
        dicts with ``shading_group`` and ``material`` keys.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        # Resolve shading engines connected to the shape(s)
        shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True) or []
        if not shapes:
            # Might already be a shape or component
            shapes = [object_name]

        shading_groups = []
        seen_sgs = set()  # type: ignore[var-annotated]

        for shape in shapes:
            sgs = cmds.listConnections(shape, type="shadingEngine") or []
            for sg in sgs:
                if sg in seen_sgs:
                    continue
                seen_sgs.add(sg)
                # Find surface shader connected to this SG
                shaders = cmds.listConnections("{}.surfaceShader".format(sg)) or []
                material = shaders[0] if shaders else ""
                shading_groups.append({"shading_group": sg, "material": material})

        return success_result(
            "Found {} shading group(s) on '{}'".format(len(shading_groups), object_name),
            object_name=object_name,
            shading_groups=shading_groups,
            count=len(shading_groups),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_shader_assignment failed")
        return error_result("Failed to get shader assignment for '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return get_shader_assignment(**kwargs)


if __name__ == "__main__":
    import json

    result = get_shader_assignment()
    print(json.dumps(result))
