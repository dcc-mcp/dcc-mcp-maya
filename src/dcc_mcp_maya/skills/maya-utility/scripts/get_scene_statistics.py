"""Query scene-level statistics: polygon counts, node counts and memory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_scene_statistics() -> dict:
    """Query scene-level statistics: polygon counts, node counts and memory.

    Returns a summary that helps an Agent understand the complexity and
    current state of the open scene without listing every individual object.

    Returns:
        ActionResultModel dict with the following context keys:

        - ``total_nodes`` — total number of DG nodes in the scene
        - ``transform_count`` — number of transform nodes
        - ``mesh_count`` — number of mesh shape nodes
        - ``poly_vertex_count`` — total polygon vertex count across all meshes
        - ``poly_face_count`` — total polygon face count across all meshes
        - ``texture_count`` — number of file texture nodes
        - ``camera_count`` — number of camera nodes
        - ``light_count`` — number of light nodes
        - ``scene_file`` — current scene file path (empty string if unsaved)
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Node counts
        all_nodes = cmds.ls() or []
        transforms = cmds.ls(type="transform") or []
        meshes = cmds.ls(type="mesh") or []
        textures = cmds.ls(type="file") or []
        cameras = cmds.ls(type="camera") or []

        # Light types present in all supported Maya versions
        light_types = [
            "pointLight",
            "directionalLight",
            "spotLight",
            "areaLight",
            "ambientLight",
            "aiAreaLight",
            "aiSkyDomeLight",
        ]
        lights = []  # type: ignore[var-annotated]
        for lt in light_types:
            lights.extend(cmds.ls(type=lt) or [])

        # Polygon statistics
        poly_verts = 0
        poly_faces = 0
        for mesh in meshes:
            try:
                poly_verts += cmds.polyEvaluate(mesh, vertex=True) or 0
                poly_faces += cmds.polyEvaluate(mesh, face=True) or 0
            except Exception:
                pass

        # Current scene file
        try:
            scene_file = cmds.file(query=True, sceneName=True) or ""
        except Exception:
            scene_file = ""

        return success_result(
            "Scene statistics: {} nodes, {} meshes, {} poly verts".format(len(all_nodes), len(meshes), poly_verts),
            total_nodes=len(all_nodes),
            transform_count=len(transforms),
            mesh_count=len(meshes),
            poly_vertex_count=poly_verts,
            poly_face_count=poly_faces,
            texture_count=len(textures),
            camera_count=len(cameras),
            light_count=len(lights),
            scene_file=scene_file,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_scene_statistics failed")
        return error_result("Failed to get scene statistics", str(exc)).to_dict()


def main(**kwargs):
    return get_scene_statistics(**kwargs)


if __name__ == "__main__":
    import json

    result = get_scene_statistics()
    print(json.dumps(result))
