"""Query which shader is assigned to an object or face set."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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

        return skill_success(
            "Found {} shading group(s) on '{}'".format(len(shading_groups), object_name),
            object_name=object_name,
            shading_groups=shading_groups,
            count=len(shading_groups),
            prompt="Use assign_material to change or set_material_attribute to adjust.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get shader assignment for '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_shader_assignment`."""
    return get_shader_assignment(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
