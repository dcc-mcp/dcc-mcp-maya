"""List all IBL / aiSkyDomeLight environment nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_hdri_nodes() -> dict:
    """List IBL and aiSkyDomeLight nodes in the current scene.

    Returns:
        ActionResultModel dict with ``nodes`` list.  Each entry contains
        ``name``, ``node_type``, ``exposure``, ``rotation_y``, and ``file_path``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        search_types = ["aiSkyDomeLight", "ambientLight", "directionalLight", "envFog"]
        nodes = []
        seen = set()

        for ntype in search_types:
            for shape in cmds.ls(type=ntype) or []:
                if shape in seen:
                    continue
                seen.add(shape)
                info = {
                    "name": shape,
                    "node_type": ntype,
                    "exposure": 0.0,
                    "rotation_y": 0.0,
                    "file_path": "",
                }

                # Exposure
                if cmds.attributeQuery("aiExposure", node=shape, exists=True):
                    try:
                        info["exposure"] = float(cmds.getAttr("{}.aiExposure".format(shape)))
                    except Exception:
                        pass
                elif cmds.attributeQuery("intensity", node=shape, exists=True):
                    try:
                        info["exposure"] = float(cmds.getAttr("{}.intensity".format(shape)))
                    except Exception:
                        pass

                # Transform rotation
                parents = cmds.listRelatives(shape, parent=True) or []
                if parents:
                    try:
                        info["rotation_y"] = float(cmds.getAttr("{}.rotateY".format(parents[0])))
                    except Exception:
                        pass

                # Linked file texture
                try:
                    conns = cmds.listConnections("{}.color".format(shape), type="file") or []
                    if conns:
                        info["file_path"] = cmds.getAttr("{}.fileTextureName".format(conns[0])) or ""
                except Exception:
                    pass

                nodes.append(info)

        return success_result(
            "Found {} HDRI/IBL node(s)".format(len(nodes)),
            prompt="Use set_hdri_exposure or set_hdri_rotation to adjust, or load_hdri to add more.",
            nodes=nodes,
            count=len(nodes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_hdri_nodes failed")
        return error_result("Failed to list HDRI nodes", str(exc)).to_dict()


def main(**kwargs):
    return list_hdri_nodes(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_hdri_nodes()))
