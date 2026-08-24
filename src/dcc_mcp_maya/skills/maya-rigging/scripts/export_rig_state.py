"""Export a bounded deterministic rig-state snapshot from Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import math
from numbers import Real
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

RIG_STATE_SCHEMA = "dcc-mcp/rig-state@1"
MAX_JOINTS = 4096
MAX_SKIN_CLUSTERS = 128
MAX_CONTROLS = 256
MAX_CONSTRAINTS = 1024
MAX_CONSTRAINT_TARGETS = 256
MAX_SKIN_VERTICES = 4096
MAX_SKIN_WEIGHT_VALUES = 65536
MAX_INFLUENCES = 256
CONSTRAINT_COMMANDS = (
    ("parentConstraint", "parentConstraint"),
    ("pointConstraint", "pointConstraint"),
    ("orientConstraint", "orientConstraint"),
    ("scaleConstraint", "scaleConstraint"),
    ("aimConstraint", "aimConstraint"),
    ("poleVectorConstraint", "poleVectorConstraint"),
)


def _canonical_dag_node(cmds, node: str, label: str) -> str:
    matches = sorted({str(item) for item in (cmds.ls(node, long=True) or [])})
    if len(matches) != 1:
        raise ValueError("{} must resolve to exactly one DAG node: {}".format(label, node))
    return matches[0]


def _bounded_nodes(cmds, explicit, node_type: str, limit: int, label: str, canonical_dag: bool = False):
    if explicit is None:
        nodes = [str(item) for item in (cmds.ls(type=node_type, long=True) or [])]
    else:
        if not isinstance(explicit, list) or len(explicit) > limit:
            raise ValueError("{} must contain at most {} nodes".format(label, limit))
        nodes = []
        for item in explicit:
            if not isinstance(item, str) or not item or len(item) > 512:
                raise ValueError("{} entries must be non-empty Maya node names".format(label))
            node = _canonical_dag_node(cmds, item, label) if canonical_dag else item
            if not cmds.objExists(node) or cmds.nodeType(node) != node_type:
                raise ValueError("{} is not a Maya {}".format(item, node_type))
            nodes.append(node)
    nodes = sorted(set(nodes))
    if len(nodes) > limit:
        raise ValueError("{} exceeds the {} node limit".format(label, limit))
    return nodes


def _joint_snapshot(cmds, joints):
    rows = []
    for joint in joints:
        parents = cmds.listRelatives(joint, parent=True, type="joint", fullPath=True) or []
        if len(parents) > 1:
            raise RuntimeError("{} reported multiple joint parents".format(joint))
        rows.append({"name": joint, "parent": str(parents[0]) if parents else None})
    return {"count": len(rows), "nodes": rows}


def _constraint_snapshot(cmds):
    rows = []
    batches = []
    total_constraints = 0
    for node_type, command_name in CONSTRAINT_COMMANDS:
        nodes = [str(item) for item in (cmds.ls(type=node_type, long=True) or [])]
        total_constraints += len(nodes)
        if total_constraints > MAX_CONSTRAINTS:
            raise ValueError("constraints exceeds the {} node limit".format(MAX_CONSTRAINTS))
        batches.append((node_type, command_name, nodes))
    for node_type, command_name, nodes in batches:
        for node in nodes:
            command = getattr(cmds, command_name)
            targets = [str(item) for item in (command(node, query=True, targetList=True) or [])]
            if len(targets) > MAX_CONSTRAINT_TARGETS:
                raise ValueError("{} exceeds the {} constraint-target limit".format(node, MAX_CONSTRAINT_TARGETS))
            canonical_targets = [_canonical_dag_node(cmds, target, "constraint target") for target in targets]
            rows.append({"name": node, "type": node_type, "targets": canonical_targets})
    rows.sort(key=lambda item: (item["type"], item["name"]))
    return {"count": len(rows), "nodes": rows}


def _skin_snapshot(cmds, clusters, tolerance):
    rows = []
    total_vertices = 0
    total_weight_values = 0
    for cluster in clusters:
        influences = [str(item) for item in (cmds.skinCluster(cluster, query=True, influence=True) or [])]
        if not influences or len(influences) > MAX_INFLUENCES:
            raise RuntimeError("{} has an invalid influence count".format(cluster))
        geometries = [str(item) for item in (cmds.skinCluster(cluster, query=True, geometry=True) or [])]
        if not geometries:
            raise RuntimeError("{} has no bound geometry".format(cluster))
        for mesh in geometries:
            vertex_count = int(cmds.polyEvaluate(mesh, vertex=True) or 0)
            if vertex_count <= 0:
                raise RuntimeError("{} did not report a positive vertex count".format(mesh))
            total_vertices += vertex_count
            if total_vertices > MAX_SKIN_VERTICES:
                raise ValueError("rig skin validation exceeds the {} total-vertex limit".format(MAX_SKIN_VERTICES))
            total_weight_values += vertex_count * len(influences)
            if total_weight_values > MAX_SKIN_WEIGHT_VALUES:
                raise ValueError("rig skin validation exceeds the {} weight-value limit".format(MAX_SKIN_WEIGHT_VALUES))
            unnormalized = 0
            for vertex in range(vertex_count):
                component = "{}.vtx[{}]".format(mesh, vertex)
                raw = cmds.skinPercent(cluster, component, query=True, value=True) or []
                if len(raw) != len(influences):
                    raise RuntimeError(
                        "{} returned {} weights for {} influences".format(component, len(raw), len(influences))
                    )
                values = [float(item) for item in raw]
                if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
                    raise RuntimeError("{} returned an invalid weight".format(component))
                if abs(sum(values) - 1.0) > tolerance:
                    unnormalized += 1
            rows.append(
                {
                    "skin_cluster": cluster,
                    "mesh": mesh,
                    "influences": influences,
                    "influence_count": len(influences),
                    "vertex_count": vertex_count,
                    "unnormalized_vertices": unnormalized,
                }
            )
            if len(rows) > MAX_SKIN_CLUSTERS:
                raise ValueError("skin geometry rows exceed the {} output limit".format(MAX_SKIN_CLUSTERS))
    rows.sort(key=lambda item: (item["skin_cluster"], item["mesh"]))
    return rows


def _control_snapshot(cmds, controls):
    if controls is None:
        shapes = [str(item) for item in (cmds.ls(type="nurbsCurve", long=True) or [])]
        control_names = []
        for shape in shapes:
            parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
            if len(parents) != 1:
                raise RuntimeError("{} did not report exactly one control parent".format(shape))
            control_names.append(str(parents[0]))
        control_names = sorted(set(control_names))
    else:
        if not isinstance(controls, list) or len(controls) > MAX_CONTROLS:
            raise ValueError("controls must contain at most {} nodes".format(MAX_CONTROLS))
        control_names = []
        for control in controls:
            if not isinstance(control, str) or not control or not cmds.objExists(control):
                raise ValueError("controls entries must be existing Maya nodes")
            control_names.append(_canonical_dag_node(cmds, control, "controls"))
        control_names = sorted(set(control_names))
    if len(control_names) > MAX_CONTROLS:
        raise ValueError("controls exceeds the {} node limit".format(MAX_CONTROLS))

    rows = []
    for control in control_names:
        shapes = [
            str(item) for item in (cmds.listRelatives(control, shapes=True, type="nurbsCurve", fullPath=True) or [])
        ]
        if not shapes:
            raise RuntimeError("{} has no NURBS control shape".format(control))
        if len(shapes) > MAX_CONTROLS:
            raise ValueError("{} exceeds the {} shape limit".format(control, MAX_CONTROLS))
        rows.append({"name": control, "shapes": sorted(set(shapes))})
    return {"count": len(rows), "nodes": rows}


def export_rig_state(
    joints: Optional[List[str]] = None,
    skin_clusters: Optional[List[str]] = None,
    controls: Optional[List[str]] = None,
    normalization_tolerance: float = 1e-4,
) -> dict:
    """Return hierarchy, constraint, control, and skin normalization evidence."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if isinstance(normalization_tolerance, bool) or not isinstance(normalization_tolerance, Real):
            return skill_error("Invalid tolerance", "normalization_tolerance must be a number")
        tolerance = float(normalization_tolerance)
        if not math.isfinite(tolerance) or tolerance <= 0.0 or tolerance > 0.1:
            return skill_error("Invalid tolerance", "normalization_tolerance must be greater than 0 and at most 0.1")
        try:
            joint_nodes = _bounded_nodes(cmds, joints, "joint", MAX_JOINTS, "joints", canonical_dag=True)
            skin_nodes = _bounded_nodes(cmds, skin_clusters, "skinCluster", MAX_SKIN_CLUSTERS, "skin_clusters")
            joint_state = _joint_snapshot(cmds, joint_nodes)
            constraint_state = _constraint_snapshot(cmds)
            skin_state = _skin_snapshot(cmds, skin_nodes, tolerance)
            control_state = _control_snapshot(cmds, controls)
        except ValueError as exc:
            return skill_error("Rig-state bounds exceeded", str(exc))

        return skill_success(
            "Exported a bounded rig-state snapshot",
            schema=RIG_STATE_SCHEMA,
            joints=joint_state,
            constraints=constraint_state,
            skins=skin_state,
            controls=control_state,
            normalization_tolerance=tolerance,
            prompt="Use typed rigging tools to repair any reported hierarchy or skin-health defect.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to export rig state")


@skill_entry
def main(**kwargs) -> dict:
    return export_rig_state(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
