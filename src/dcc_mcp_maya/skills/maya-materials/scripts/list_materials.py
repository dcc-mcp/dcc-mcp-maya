"""List all material nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def list_materials(shader_type: Optional[str] = None) -> dict:
    """List all material nodes in the scene.

    Args:
        shader_type: Optional filter by shader type (e.g. ``"lambert"``).

    Returns:
        ToolResult dict with ``context.materials`` list.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if shader_type:
            materials = cmds.ls(type=shader_type) or []
        else:
            all_shaders = []
            for st in _SUPPORTED_SHADERS:
                all_shaders.extend(cmds.ls(type=st) or [])
            # Also catch any user-created materials not in known list
            all_shaders.extend(cmds.ls(materials=True) or [])
            # Deduplicate preserving order
            seen = set()  # type: ignore[var-annotated]
            materials = []  # type: List[str]
            for m in all_shaders:
                if m not in seen:
                    seen.add(m)
                    materials.append(m)

        return skill_success(
            "Found {} material(s)".format(len(materials)),
            materials=[{"name": m} for m in materials],
            count=len(materials),
            prompt="Use assign_material or set_material_attribute to manage the listed shaders.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list materials")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_materials`."""
    return list_materials(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
