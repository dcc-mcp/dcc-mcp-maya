"""Return a hierarchical DAG description of the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import node_ref_from_name, object_transform_from_node

_DETAIL_MODES = ("lightweight", "standard", "full")


def _short_name(long_name: str) -> str:
    return long_name.rsplit("|", 1)[-1] if "|" in long_name else long_name


def _safe_parent(cmds, node_name: str):
    try:
        parents = cmds.listRelatives(node_name, parent=True, fullPath=True) or []
    except Exception:
        return None
    return parents[0] if parents else None


def _safe_children(cmds, node_name: str):
    try:
        return cmds.listRelatives(node_name, children=True, fullPath=True) or []
    except Exception:
        return []


def _safe_visible(cmds, node_name: str) -> bool:
    try:
        return bool(cmds.getAttr(node_name + ".visibility"))
    except Exception:
        return True


def _safe_object_type(cmds, node_name: str):
    try:
        return cmds.objectType(node_name)
    except Exception:
        return None


def _current_scene_path(cmds):
    try:
        scene_path = cmds.file(query=True, sceneName=True)
    except Exception:
        return None
    return scene_path or None


def get_scene_info(include_transforms: bool = True, detail_mode: str = "full") -> dict:
    """Return a hierarchical DAG description of the current scene.

    For each DAG transform node the result includes the node's name, type,
    direct parent and immediate children so callers can reconstruct the full
    hierarchy without additional queries.

    Uses :func:`dcc_mcp_maya.api.scene_object_from_node` and
    :func:`dcc_mcp_maya.api.object_transform_from_node` to produce
    ``SceneObject``- and ``ObjectTransform``-compatible dicts for
    cross-DCC interoperability.

    Args:
        include_transforms: If True (default), each node entry also carries its
            world-space translate/rotate/scale values via ``ObjectTransform``
            schema.
        detail_mode: Payload/cost profile. ``lightweight`` returns only the DAG
            skeleton and basic node fields, ``standard`` also includes
            ``node_ref``, and ``full`` keeps the historical payload including
            transforms unless ``include_transforms`` is False.

    Returns:
        ToolResult dict with ``context.nodes`` (list of dicts) and
        ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if detail_mode not in _DETAIL_MODES:
            return skill_error(
                "Invalid detail_mode",
                "detail_mode must be one of: {}".format(", ".join(_DETAIL_MODES)),
            )

        transforms = cmds.ls(type="transform", l=True) or []
        scene_path = _current_scene_path(cmds) if detail_mode in ("standard", "full") else None
        nodes = []
        for long_name in transforms:
            object_type = _safe_object_type(cmds, long_name)
            node = {
                "name": _short_name(long_name),
                "long_name": long_name,
                "object_type": object_type,
                "parent": _safe_parent(cmds, long_name),
                "visible": _safe_visible(cmds, long_name),
                "metadata": {},
                "children": _safe_children(cmds, long_name),
            }
            if detail_mode in ("standard", "full"):
                node["node_ref"] = node_ref_from_name(
                    cmds,
                    long_name,
                    scene_path=scene_path,
                    node_type=object_type,
                    exists=True,
                )
            if detail_mode == "full" and include_transforms:
                try:
                    xform = object_transform_from_node(cmds, long_name)
                    node["translate"] = xform["translate"]
                    node["rotate"] = xform["rotate"]
                    node["scale"] = xform["scale"]
                except Exception:
                    pass
            nodes.append(node)

        return skill_success(
            "Scene info: {} transform node(s)".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
            detail_mode=detail_mode,
            prompt="Use set_transform or assign_material to modify listed objects.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get scene info")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_scene_info`."""
    return get_scene_info(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
