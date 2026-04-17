"""List all IBL / aiSkyDomeLight environment nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_hdri_nodes() -> dict:
    """List IBL and aiSkyDomeLight nodes in the current scene.

    Returns:
        ToolResult dict with ``nodes`` list.  Each entry contains
        ``name``, ``node_type``, ``exposure``, ``rotation_y``, and ``file_path``.
    """
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

        return skill_success(
            "Found {} HDRI/IBL node(s)".format(len(nodes)),
            prompt="Use set_hdri_exposure or set_hdri_rotation to adjust, or load_hdri to add more.",
            nodes=nodes,
            count=len(nodes),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list HDRI nodes")


@skill_entry
def main(**kwargs):
    return list_hdri_nodes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
