"""List all shading engine (shadingEngine) nodes in the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def list_shading_groups() -> dict:
    """List all shading engine (shadingEngine) nodes in the current scene.

    Provides a scene-level view of every shading group, including the
    assigned surface shader and the number of members.

    Returns:
        ToolResult dict with ``context.shading_groups`` — a list of
        dicts with ``name``, ``surface_shader``, ``shader_type``,
        ``member_count`` keys, and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        sgs = cmds.ls(type="shadingEngine") or []
        result = []
        for sg in sgs:
            shaders = cmds.listConnections("{}.surfaceShader".format(sg)) or []
            surface_shader = shaders[0] if shaders else ""
            shader_type = cmds.nodeType(surface_shader) if surface_shader else ""
            try:
                members = cmds.sets(sg, query=True) or []
                member_count = len(members)
            except Exception:
                member_count = 0
            result.append(
                {
                    "name": sg,
                    "surface_shader": surface_shader,
                    "shader_type": shader_type,
                    "member_count": member_count,
                }
            )

        return skill_success(
            "Found {} shading group(s)".format(len(result)),
            shading_groups=result,
            count=len(result),
            prompt="Use assign_material or get_shader_assignment to inspect.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list shading groups")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_shading_groups`."""
    return list_shading_groups(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
