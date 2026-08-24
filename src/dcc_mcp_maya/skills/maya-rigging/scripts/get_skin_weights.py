"""Read a bounded set of per-vertex skin weights with normalization evidence."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import math
from numbers import Real
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

SKIN_WEIGHTS_SCHEMA = "dcc-mcp/skin-weights@1"
MAX_VERTICES = 4096
MAX_INFLUENCES = 256
MAX_WEIGHT_VALUES = 65536


def _find_skin_cluster(cmds, mesh: str, skin_cluster: Optional[str]) -> str:
    if skin_cluster:
        if cmds.objExists(skin_cluster) and cmds.nodeType(skin_cluster) == "skinCluster":
            return skin_cluster
        raise ValueError("skin_cluster must reference one existing Maya skinCluster")
    history = cmds.listHistory(mesh) or []
    clusters = sorted({str(item) for item in (cmds.ls(history, type="skinCluster") or [])})
    if len(clusters) != 1:
        raise ValueError("mesh history must resolve to exactly one skinCluster; pass skin_cluster explicitly")
    return clusters[0]


def get_skin_weights(
    mesh: str,
    skin_cluster: Optional[str] = None,
    vertices: Optional[List[int]] = None,
    normalization_tolerance: float = 1e-4,
) -> dict:
    """Return weights for explicit vertices, or all vertices when safely bounded."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not isinstance(mesh, str) or not mesh or len(mesh) > 256:
            return skill_error("Invalid mesh", "mesh must be one non-empty Maya node name")
        if not cmds.objExists(mesh):
            return skill_error("Mesh not found", "{} does not exist".format(mesh))
        try:
            cluster = _find_skin_cluster(cmds, mesh, skin_cluster)
        except ValueError as exc:
            return skill_error("Skin cluster resolution failed", str(exc))
        influences = [str(item) for item in (cmds.skinCluster(cluster, query=True, influence=True) or [])]
        if not influences or len(influences) > MAX_INFLUENCES:
            return skill_error(
                "Invalid skin influences",
                "skinCluster must have between 1 and {} influences".format(MAX_INFLUENCES),
            )

        mesh_vertex_count = int(cmds.polyEvaluate(mesh, vertex=True) or 0)
        if mesh_vertex_count <= 0:
            return skill_error("Mesh has no vertices", "{} did not report a positive vertex count".format(mesh))
        if vertices is None:
            if mesh_vertex_count > MAX_VERTICES:
                return skill_error(
                    "Mesh exceeds the read limit",
                    "Pass an explicit vertices subset of at most {} indices".format(MAX_VERTICES),
                )
            vertex_indices = list(range(mesh_vertex_count))
        else:
            if not isinstance(vertices, list) or not 1 <= len(vertices) <= MAX_VERTICES:
                return skill_error(
                    "Invalid vertex selection",
                    "vertices must contain between 1 and {} indices".format(MAX_VERTICES),
                )
            if any(isinstance(index, bool) or not isinstance(index, int) for index in vertices):
                return skill_error("Invalid vertex selection", "vertex indices must be integers")
            vertex_indices = list(vertices)
            if len(set(vertex_indices)) != len(vertex_indices) or any(
                index < 0 or index >= mesh_vertex_count for index in vertex_indices
            ):
                return skill_error("Invalid vertex selection", "vertex indices must be unique and within the mesh")
        if len(vertex_indices) * len(influences) > MAX_WEIGHT_VALUES:
            return skill_error(
                "Skin-weight read is too large",
                "requested matrix exceeds the {} weight-value limit; pass a smaller vertices subset".format(
                    MAX_WEIGHT_VALUES
                ),
            )
        if isinstance(normalization_tolerance, bool) or not isinstance(normalization_tolerance, Real):
            return skill_error("Invalid tolerance", "normalization_tolerance must be a number")
        tolerance = float(normalization_tolerance)
        if not math.isfinite(tolerance) or tolerance <= 0.0 or tolerance > 0.1:
            return skill_error("Invalid tolerance", "normalization_tolerance must be greater than 0 and at most 0.1")

        rows = []
        unnormalized = 0
        for index in vertex_indices:
            component = "{}.vtx[{}]".format(mesh, index)
            raw = cmds.skinPercent(cluster, component, query=True, value=True) or []
            if len(raw) != len(influences):
                return skill_error(
                    "Skin-weight readback failed",
                    "{} returned {} weights for {} influences".format(component, len(raw), len(influences)),
                )
            values = [float(item) for item in raw]
            if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
                return skill_error("Skin-weight readback failed", "{} returned an invalid weight".format(component))
            total = float(sum(values))
            if abs(total - 1.0) > tolerance:
                unnormalized += 1
            rows.append(
                {
                    "vertex": index,
                    "weights": [
                        {"influence": influence, "weight": value} for influence, value in zip(influences, values)
                    ],
                    "total_weight": total,
                }
            )

        return skill_success(
            "Read skin weights for {} vertices".format(len(rows)),
            schema=SKIN_WEIGHTS_SCHEMA,
            mesh=mesh,
            skin_cluster=cluster,
            influences=influences,
            influence_count=len(influences),
            vertices=rows,
            vertex_count=len(rows),
            mesh_vertex_count=mesh_vertex_count,
            unnormalized_vertices=unnormalized,
            normalization_tolerance=tolerance,
            prompt="Use set_skin_weights with complete normalized rows for bounded repair.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to read skin weights")


@skill_entry
def main(**kwargs) -> dict:
    return get_skin_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
