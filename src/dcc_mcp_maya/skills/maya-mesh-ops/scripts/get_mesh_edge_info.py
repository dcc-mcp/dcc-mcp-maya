"""Query edge length and connected vertex indices for a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_mesh_edge_info(
    object_name: str,
    edge_indices: Optional[List[int]] = None,
) -> dict:
    """Query edge length and connected vertex indices for a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        edge_indices: Optional list of zero-based edge indices to query.
            If None, all edges are queried (may be slow on dense meshes).

    Returns:
        ActionResultModel dict with ``context.edges`` (list of dicts with
        ``index``, ``length``, ``vertices``), ``context.edge_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        total_edges = cmds.polyEvaluate(object_name, edge=True)
        if not isinstance(total_edges, int) or total_edges == 0:
            return error_result("'{}' has no edges — ensure it is a polygon mesh".format(object_name)).to_dict()

        if edge_indices is None:
            indices = list(range(total_edges))
        else:
            invalid = [i for i in edge_indices if not (0 <= i < total_edges)]
            if invalid:
                return error_result(
                    "Invalid edge indices: {}".format(invalid),
                    "Valid range is 0 to {}".format(total_edges - 1),
                ).to_dict()
            indices = list(edge_indices)

        edges = []
        for idx in indices:
            edge_comp = "{}.e[{}]".format(object_name, idx)
            # Edge length via polyInfo
            try:
                info_lines = cmds.polyInfo(edge_comp, edgeToVertex=True) or []
                verts = []
                for line in info_lines:
                    parts = line.strip().split()
                    # Format: EDGE n : v1 v2
                    colon_pos = [i for i, p in enumerate(parts) if p == ":"]
                    if colon_pos:
                        for p in parts[colon_pos[0] + 1 :]:
                            try:
                                verts.append(int(p))
                            except ValueError:
                                pass
            except Exception:
                verts = []

            try:
                _ = cmds.polyInfo(edge_comp, edgeToFace=False) or []
                # Edge length via arclen approximation
                length = None
                if verts and len(verts) >= 2:
                    v0_pos = cmds.pointPosition("{}.vtx[{}]".format(object_name, verts[0]), world=True)
                    v1_pos = cmds.pointPosition("{}.vtx[{}]".format(object_name, verts[1]), world=True)
                    length = (
                        (v1_pos[0] - v0_pos[0]) ** 2 + (v1_pos[1] - v0_pos[1]) ** 2 + (v1_pos[2] - v0_pos[2]) ** 2
                    ) ** 0.5
                    length = round(length, 6)
            except Exception:
                length = None

            edges.append({"index": idx, "length": length, "vertices": verts})

        return success_result(
            "Edge info for '{}' ({} edge(s) queried)".format(object_name, len(edges)),
            object_name=object_name,
            edges=edges,
            edge_count=len(edges),
            total_edges=total_edges,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_mesh_edge_info failed")
        return error_result("Failed to get edge info", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_mesh_edge_info`."""
    return get_mesh_edge_info(**kwargs)


if __name__ == "__main__":
    import json

    result = get_mesh_edge_info()
    print(json.dumps(result))
