"""List all material nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def list_materials(shader_type: Optional[str] = None) -> dict:
    """List all material nodes in the scene.

    Args:
        shader_type: Optional filter by shader type (e.g. ``"lambert"``).

    Returns:
        ActionResultModel dict with ``context.materials`` list.
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

        return maya_success(
            "Found {} material(s)".format(len(materials)),
            materials=materials,
            count=len(materials),
            prompt="Use assign_material or set_material_attribute to manage the listed shaders.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list materials")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_materials`."""
    return list_materials(**kwargs)


if __name__ == "__main__":
    import json

    result = list_materials()
    print(json.dumps(result))
