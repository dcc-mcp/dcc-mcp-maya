"""Replace bounded per-vertex skin weights and verify native readback."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import math
from numbers import Real
from typing import Dict, List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

SKIN_WEIGHTS_SCHEMA = "dcc-mcp/skin-weights@1"
MAX_VERTICES = 4096
MAX_INFLUENCES = 256
MAX_WEIGHT_VALUES = 65536


def _find_skin_cluster(cmds, mesh: str, skin_cluster: Optional[str]) -> Optional[str]:
    if skin_cluster:
        if cmds.objExists(skin_cluster) and cmds.nodeType(skin_cluster) == "skinCluster":
            return skin_cluster
        return None
    history = cmds.listHistory(mesh) or []
    clusters = cmds.ls(history, type="skinCluster") or []
    return str(clusters[0]) if clusters else None


def _validate_rows(
    rows: List[dict],
    influence_names: List[str],
    mesh_vertex_count: int,
    tolerance: float,
):
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_VERTICES:
        raise ValueError("vertices must contain between 1 and {} rows".format(MAX_VERTICES))
    if len(rows) * len(influence_names) > MAX_WEIGHT_VALUES:
        raise ValueError("requested readback exceeds the {} weight-value limit".format(MAX_WEIGHT_VALUES))

    allowed = set(influence_names)
    seen_vertices = set()
    validated = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"vertex", "weights"}:
            raise ValueError("each vertex row must contain only vertex and weights")
        vertex = row["vertex"]
        if isinstance(vertex, bool) or not isinstance(vertex, int):
            raise ValueError("vertex indices must be integers")
        if vertex < 0 or vertex >= mesh_vertex_count or vertex in seen_vertices:
            raise ValueError("vertex indices must be unique and within the mesh")
        seen_vertices.add(vertex)

        weights = row["weights"]
        if not isinstance(weights, list) or not 1 <= len(weights) <= MAX_INFLUENCES:
            raise ValueError("each weights array must contain 1 to {} entries".format(MAX_INFLUENCES))
        seen_influences = set()
        pairs = []
        for item in weights:
            if not isinstance(item, dict) or set(item) != {"influence", "weight"}:
                raise ValueError("each weight must contain only influence and weight")
            influence = item["influence"]
            if not isinstance(influence, str) or influence not in allowed or influence in seen_influences:
                raise ValueError("weight influences must be unique members of the skinCluster")
            seen_influences.add(influence)
            if isinstance(item["weight"], bool) or not isinstance(item["weight"], Real):
                raise ValueError("weights must be numbers between 0 and 1")
            value = float(item["weight"])
            if not math.isfinite(value) or value < 0.0 or value > 1.0:
                raise ValueError("weights must be finite numbers between 0 and 1")
            pairs.append((influence, value))
        if abs(sum(value for _influence, value in pairs) - 1.0) > tolerance:
            raise ValueError("each vertex row must sum to 1 within normalization_tolerance")
        validated.append((vertex, pairs))
    return validated


def _read_row(cmds, cluster: str, mesh: str, vertex: int, influences: List[str]):
    component = "{}.vtx[{}]".format(mesh, vertex)
    raw = cmds.skinPercent(cluster, component, query=True, value=True) or []
    if len(raw) != len(influences):
        raise RuntimeError("{} returned {} weights for {} influences".format(component, len(raw), len(influences)))
    values = [float(item) for item in raw]
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise RuntimeError("{} returned an invalid weight".format(component))
    return values


def set_skin_weights(
    mesh: str,
    vertices: List[dict],
    skin_cluster: Optional[str] = None,
    normalization_tolerance: float = 1e-4,
) -> dict:
    """Replace complete normalized rows, then verify the effective values."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not isinstance(mesh, str) or not mesh or len(mesh) > 256:
            return skill_error("Invalid mesh", "mesh must be one non-empty Maya node name")
        if not cmds.objExists(mesh):
            return skill_error("Mesh not found", "{} does not exist".format(mesh))
        cluster = _find_skin_cluster(cmds, mesh, skin_cluster)
        if cluster is None:
            return skill_error("Skin cluster not found", "{} has no usable skinCluster".format(mesh))
        influences = [str(item) for item in (cmds.skinCluster(cluster, query=True, influence=True) or [])]
        if not influences or len(influences) > MAX_INFLUENCES:
            return skill_error(
                "Invalid skin influences",
                "skinCluster must have between 1 and {} influences".format(MAX_INFLUENCES),
            )
        mesh_vertex_count = int(cmds.polyEvaluate(mesh, vertex=True) or 0)
        if mesh_vertex_count <= 0:
            return skill_error("Mesh has no vertices", "{} did not report a positive vertex count".format(mesh))
        if isinstance(normalization_tolerance, bool) or not isinstance(normalization_tolerance, Real):
            return skill_error("Invalid tolerance", "normalization_tolerance must be a number")
        tolerance = float(normalization_tolerance)
        if not math.isfinite(tolerance) or tolerance <= 0.0 or tolerance > 0.1:
            return skill_error("Invalid tolerance", "normalization_tolerance must be greater than 0 and at most 0.1")
        try:
            validated = _validate_rows(vertices, influences, mesh_vertex_count, tolerance)
        except (TypeError, ValueError) as exc:
            return skill_error("Invalid skin weights", str(exc))

        expected_by_vertex: Dict[int, Dict[str, float]] = {}
        for vertex, pairs in validated:
            component = "{}.vtx[{}]".format(mesh, vertex)
            cmds.skinPercent(
                cluster,
                component,
                transformValue=pairs,
                normalize=True,
                zeroRemainingInfluences=True,
            )
            expected_by_vertex[vertex] = dict(pairs)

        output_rows = []
        for vertex, _pairs in validated:
            values = _read_row(cmds, cluster, mesh, vertex, influences)
            expected = expected_by_vertex[vertex]
            for influence, value in zip(influences, values):
                if abs(value - expected.get(influence, 0.0)) > tolerance:
                    return skill_error(
                        "Skin-weight verification failed",
                        "{}.vtx[{}] did not preserve the requested {} weight".format(mesh, vertex, influence),
                    )
            total = float(sum(values))
            if abs(total - 1.0) > tolerance:
                return skill_error(
                    "Skin-weight verification failed",
                    "{}.vtx[{}] is not normalized after the write".format(mesh, vertex),
                )
            output_rows.append(
                {
                    "vertex": vertex,
                    "weights": [
                        {"influence": influence, "weight": value} for influence, value in zip(influences, values)
                    ],
                    "total_weight": total,
                }
            )

        return skill_success(
            "Set and verified skin weights for {} vertices".format(len(output_rows)),
            schema=SKIN_WEIGHTS_SCHEMA,
            mesh=mesh,
            skin_cluster=cluster,
            influences=influences,
            influence_count=len(influences),
            vertices=output_rows,
            vertex_count=len(output_rows),
            mesh_vertex_count=mesh_vertex_count,
            verified_vertex_count=len(output_rows),
            unnormalized_vertices=0,
            normalization_tolerance=tolerance,
            prompt="Use get_skin_weights to inspect another bounded vertex subset.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set skin weights")


@skill_entry
def main(**kwargs) -> dict:
    return set_skin_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
