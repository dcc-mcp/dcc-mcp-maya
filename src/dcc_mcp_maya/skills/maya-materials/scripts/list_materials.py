"""List all material nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def list_materials(shader_type: Optional[str] = None) -> dict:
    """List all material nodes in the scene.

    Args:
        shader_type: Optional filter by shader type (e.g. ``"lambert"``).

    Returns:
        ActionResultModel dict with ``context.materials`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} material(s)".format(len(materials)),
            materials=materials,
            count=len(materials),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_materials failed")
        return error_result("Failed to list materials", str(exc)).to_dict()


def main(**kwargs):
    return list_materials(**kwargs)


if __name__ == "__main__":
    import json

    result = list_materials()
    print(json.dumps(result))
