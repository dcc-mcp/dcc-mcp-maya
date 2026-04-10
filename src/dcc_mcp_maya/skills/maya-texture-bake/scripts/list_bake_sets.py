"""List bake set nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_bake_sets() -> dict:
    """List all bake set nodes in the current Maya scene.

    Bake sets are special ``objectSet`` nodes used by Maya's ``convertLightmap``
    and Transfer Maps workflows to store bake parameters.

    Returns:
        ActionResultModel dict with ``bake_sets`` list.  Each entry contains
        ``name``, ``resolution``, ``file_format``, and ``members``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        all_sets = cmds.ls(type="objectSet") or []
        bake_sets = []
        for s in all_sets:
            if not cmds.attributeQuery("bakeResolutionX", node=s, exists=True):
                continue
            info = {
                "name": s,
                "resolution_x": 1024,
                "resolution_y": 1024,
                "file_format": "",
                "members": [],
            }
            try:
                info["resolution_x"] = int(cmds.getAttr("{}.bakeResolutionX".format(s)))
            except Exception:
                pass
            try:
                info["resolution_y"] = int(cmds.getAttr("{}.bakeResolutionY".format(s)))
            except Exception:
                pass
            try:
                info["file_format"] = cmds.getAttr("{}.fileFormat".format(s)) or ""
            except Exception:
                pass
            try:
                info["members"] = cmds.sets(s, query=True) or []
            except Exception:
                pass
            bake_sets.append(info)

        return success_result(
            "Found {} bake set(s)".format(len(bake_sets)),
            prompt="Use bake_lighting or transfer_maps to bake, or bake_ambient_occlusion for AO.",
            bake_sets=bake_sets,
            count=len(bake_sets),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_bake_sets failed")
        return error_result("Failed to list bake sets", str(exc)).to_dict()


def main(**kwargs):
    return list_bake_sets(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_bake_sets()))
