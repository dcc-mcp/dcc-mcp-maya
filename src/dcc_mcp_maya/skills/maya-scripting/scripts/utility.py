"""General-purpose Maya utility actions.

Provides actions that do not fit neatly into a single domain category but
are broadly useful for working with Maya scenes:

- :func:`create_utility_node` — instantiate any Maya utility/shading node
- :func:`get_scene_statistics` — query polygon counts, node counts and memory
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_utility_node(
    node_type: str,
    name: Optional[str] = None,
) -> dict:
    """Create any Maya utility or shading node by type.

    This is a generic factory action that complements :func:`create_material`
    for cases where the Agent needs a specific utility node (e.g.
    ``multiplyDivide``, ``reverse``, ``condition``, ``remapValue``,
    ``blendColors``, ``samplerInfo``, etc.).

    Args:
        node_type: Maya node type string (e.g. ``"multiplyDivide"``,
            ``"condition"``, ``"reverse"``).
        name: Optional name for the created node.  When omitted Maya
            auto-generates one.

    Returns:
        ActionResultModel dict with ``context.node_name`` and
        ``context.node_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not node_type or not node_type.strip():
            return error_result("Invalid node_type", "node_type must not be empty").to_dict()

        node = cmds.shadingNode(node_type, asUtility=True)

        if name and name.strip():
            node = cmds.rename(node, name)

        return success_result(
            "Created utility node '{}' of type '{}'".format(node, node_type),
            node_name=node,
            node_type=node_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_utility_node failed")
        return error_result("Failed to create utility node of type '{}'".format(node_type), str(exc)).to_dict()


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
