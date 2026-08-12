"""Create an editable, cluster-tagged hair guide curve."""

import math
from statistics import median
from typing import List, Optional, Sequence, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception

from dcc_mcp_maya._guide_curve_types import GuideCurveResult
from dcc_mcp_maya.api import maya_typed_success

_ATTR_CLUSTER_ID = "dccGuideClusterId"
_ATTR_ROOT_TO_TIP = "dccGuideRootToTip"
_ATTR_SOURCE_VIEW = "dccGuideSourceView"
_ATTR_DOMINANT_CLUMP = "dccGuideDominantClump"
_MAX_CLUSTER_ID_LENGTH = 64
_MAX_SOURCE_VIEW_LENGTH = 64
_MAX_DOMINANT_CLUMP_LENGTH = 128


def _validate_label(value: Optional[str], field: str, max_length: int, required: bool = False) -> Optional[str]:
    if value is None:
        if required:
            raise ValueError("{} is required".format(field))
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("{} must be a non-empty string without surrounding whitespace".format(field))
    if len(value) > max_length:
        raise ValueError("{} must contain at most {} characters".format(field, max_length))
    if not value[0].isascii() or not value[0].isalnum():
        raise ValueError("{} must start with an ASCII letter or number".format(field))
    if any(not char.isascii() or not (char.isalnum() or char in "_.-") for char in value):
        raise ValueError("{} may contain only letters, numbers, '_', '-', and '.'".format(field))
    return value


def _validate_points(points: Optional[Sequence[Sequence[float]]], degree: int) -> List[List[float]]:
    if not isinstance(degree, int) or isinstance(degree, bool) or not 1 <= degree <= 7:
        raise ValueError("degree must be an integer between 1 and 7")
    if points is None or len(points) < degree + 1:
        count = 0 if points is None else len(points)
        raise ValueError("Need at least {} points for degree-{} guide curve, got {}".format(degree + 1, degree, count))

    validated = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 3:
            raise ValueError("points[{}] must contain exactly three coordinates".format(index))
        coordinates = [float(value) for value in point]
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError("points[{}] coordinates must be finite".format(index))
        validated.append(coordinates)
    return validated


def _validate_color(display_color_rgb: Optional[Sequence[float]]) -> List[float]:
    if not isinstance(display_color_rgb, (list, tuple)) or len(display_color_rgb) != 3:
        raise ValueError("display_color_rgb must contain exactly three values")
    color = [float(value) for value in display_color_rgb]
    if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in color):
        raise ValueError("display_color_rgb values must be finite numbers between 0 and 1")
    return color


def _read_rgb_attribute(value) -> Optional[List[float]]:
    if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], (list, tuple)):
        value = value[0]
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    color = [float(component) for component in value]
    return color if all(math.isfinite(component) for component in color) else None


def _cluster_state(cmds, cluster_id: str) -> Tuple[List[float], Optional[List[float]]]:
    lengths = []
    cluster_color = None
    for node in cmds.ls("*.{}".format(_ATTR_CLUSTER_ID), objectsOnly=True, long=True) or []:
        try:
            if cmds.getAttr("{}.{}".format(node, _ATTR_CLUSTER_ID)) != cluster_id:
                continue
        except Exception:  # noqa: BLE001 - stale tagged nodes are ignored
            continue
        try:
            length = float(cmds.arclen(node))
            if math.isfinite(length) and length > 0.0:
                lengths.append(length)
        except Exception:  # noqa: BLE001 - a non-curve tagged node has no usable length
            pass
        try:
            shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True) or []
            if not shapes:
                continue
            color = _read_rgb_attribute(cmds.getAttr("{}.overrideColorRGB".format(shapes[0])))
            if color is None:
                continue
            if cluster_color is None:
                cluster_color = color
            elif any(abs(current - expected) > 1e-6 for current, expected in zip(color, cluster_color)):
                raise ValueError("Existing cluster '{}' contains inconsistent viewport colors".format(cluster_id))
        except ValueError:
            raise
        except Exception:  # noqa: BLE001 - legacy guides may not expose RGB overrides
            continue
    return lengths, cluster_color


def _set_string_attribute(cmds, node: str, attribute: str, value: Optional[str]) -> None:
    if value is None:
        return
    if not cmds.attributeQuery(attribute, node=node, exists=True):
        cmds.addAttr(node, longName=attribute, dataType="string")
    cmds.setAttr("{}.{}".format(node, attribute), value, type="string")


def _set_bool_attribute(cmds, node: str, attribute: str, value: bool) -> None:
    if not cmds.attributeQuery(attribute, node=node, exists=True):
        cmds.addAttr(node, longName=attribute, attributeType="bool")
    cmds.setAttr("{}.{}".format(node, attribute), value)


def _delete_curve_quietly(cmds, curve: Optional[str]) -> None:
    if cmds is None or curve is None:
        return
    try:
        cmds.delete(curve)
    except Exception:  # noqa: BLE001 - cleanup must preserve the original result
        pass


def _resolve_mesh_shape(cmds, scalp_mesh: str) -> str:
    if not cmds.objExists(scalp_mesh):
        raise ValueError("scalp_mesh '{}' does not exist".format(scalp_mesh))
    if cmds.nodeType(scalp_mesh) == "mesh":
        return scalp_mesh
    shapes = cmds.listRelatives(scalp_mesh, shapes=True, noIntermediate=True, fullPath=True) or []
    mesh_shapes = [shape for shape in shapes if cmds.nodeType(shape) == "mesh"]
    if not mesh_shapes:
        raise ValueError("scalp_mesh '{}' has no mesh shape".format(scalp_mesh))
    return mesh_shapes[0]


def _validate_node_reference(value: str, field: str, max_length: int) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("{} must be a non-empty string without surrounding whitespace".format(field))
    if len(value) > max_length:
        raise ValueError("{} must contain at most {} characters".format(field, max_length))
    return value


def _root_projection_distance(cmds, scalp_mesh: str, root_position: Sequence[float]) -> Tuple[float, str]:
    from maya.api import OpenMaya as om  # noqa: PLC0415

    mesh_shape = _resolve_mesh_shape(cmds, scalp_mesh)
    selection = om.MSelectionList()
    selection.add(mesh_shape)
    dag_path = selection.getDagPath(0)
    closest_point, _face_id = om.MFnMesh(dag_path).getClosestPoint(
        om.MPoint(*root_position),
        om.MSpace.kWorld,
    )
    delta = closest_point - om.MPoint(*root_position)
    return float(delta.length()), mesh_shape


def create_guide_curve(
    points: Optional[List[List[float]]] = None,
    cluster_id: Optional[str] = None,
    display_color_rgb: Optional[List[float]] = None,
    name: Optional[str] = None,
    degree: int = 3,
    root_to_tip: bool = True,
    scalp_mesh: Optional[str] = None,
    source_view: Optional[str] = None,
    dominant_clump: Optional[str] = None,
    length_tolerance_ratio: float = 0.1,
) -> dict:
    """Create an open guide curve with bounded metadata and measurements.

    Input points are always interpreted in scalp-root to tip order. Existing
    curves carrying the same cluster ID and the candidate define the cluster
    median arc length; an invalid candidate is deleted before an error returns.
    """

    created_curve = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if root_to_tip is not True:
            raise ValueError("root_to_tip must be true for editable guide curves")
        cluster_id = _validate_label(cluster_id, "cluster_id", _MAX_CLUSTER_ID_LENGTH, required=True)
        source_view = _validate_label(source_view, "source_view", _MAX_SOURCE_VIEW_LENGTH)
        dominant_clump = _validate_label(dominant_clump, "dominant_clump", _MAX_DOMINANT_CLUMP_LENGTH)
        validated_points = _validate_points(points, degree)
        color = _validate_color(display_color_rgb)
        tolerance = float(length_tolerance_ratio)
        if not math.isfinite(tolerance) or tolerance <= 0.0 or tolerance > 0.1:
            raise ValueError("length_tolerance_ratio must be greater than 0 and at most 0.1")

        resolved_scalp = None
        if scalp_mesh is not None:
            scalp_mesh = _validate_node_reference(scalp_mesh, "scalp_mesh", 256)
            resolved_scalp = _resolve_mesh_shape(cmds, scalp_mesh)

        existing_lengths, existing_color = _cluster_state(cmds, cluster_id)
        if existing_color is not None and any(
            abs(requested - current) > 1e-6 for requested, current in zip(color, existing_color)
        ):
            raise ValueError("display_color_rgb must match the existing color for cluster '{}'".format(cluster_id))
        curve_kwargs = {
            "point": [tuple(point) for point in validated_points],
            "degree": degree,
            "periodic": 0,
        }
        if name:
            curve_kwargs["name"] = name
        created_curve = cmds.curve(**curve_kwargs)

        arc_length = float(cmds.arclen(created_curve))
        if not math.isfinite(arc_length) or arc_length <= 0.0:
            raise ValueError("Guide curve arc length must be greater than zero")
        candidate_lengths = existing_lengths + [arc_length]
        cluster_median = float(median(candidate_lengths))
        cluster_deviations = [abs(length / cluster_median - 1.0) for length in candidate_lengths]
        deviation = cluster_deviations[-1]
        if any(
            current > tolerance and not math.isclose(current, tolerance, rel_tol=0.0, abs_tol=1e-12)
            for current in cluster_deviations
        ):
            _delete_curve_quietly(cmds, created_curve)
            created_curve = None
            return skill_error(
                "Guide curve length exceeds {:g}% cluster tolerance".format(tolerance * 100.0),
                "arc_length={} cluster_median={} deviation_ratio={} max_deviation_ratio={} tolerance={}".format(
                    arc_length,
                    cluster_median,
                    deviation,
                    max(cluster_deviations),
                    tolerance,
                ),
            )

        shapes = cmds.listRelatives(created_curve, shapes=True, noIntermediate=True, fullPath=True) or []
        if not shapes:
            raise ValueError("Created guide curve has no NURBS shape")
        shape = shapes[0]
        cmds.setAttr("{}.overrideEnabled".format(shape), True)
        cmds.setAttr("{}.overrideRGBColors".format(shape), True)
        cmds.setAttr("{}.overrideColorRGB".format(shape), color[0], color[1], color[2])

        _set_string_attribute(cmds, created_curve, _ATTR_CLUSTER_ID, cluster_id)
        _set_bool_attribute(cmds, created_curve, _ATTR_ROOT_TO_TIP, True)
        _set_string_attribute(cmds, created_curve, _ATTR_SOURCE_VIEW, source_view)
        _set_string_attribute(cmds, created_curve, _ATTR_DOMINANT_CLUMP, dominant_clump)

        projection_distance = None
        if resolved_scalp is not None:
            projection_distance, resolved_scalp = _root_projection_distance(
                cmds,
                resolved_scalp,
                validated_points[0],
            )

        typed_result = GuideCurveResult(
            transform=created_curve,
            shape=shape,
            degree=degree,
            cv_count=len(validated_points),
            cluster_id=cluster_id,
            display_color_rgb=color,
            root_to_tip=True,
            root_position=list(validated_points[0]),
            tip_position=list(validated_points[-1]),
            arc_length=arc_length,
            cluster_median_arc_length=cluster_median,
            length_deviation_ratio=deviation,
            root_projection_distance=projection_distance,
            scalp_mesh=resolved_scalp,
            source_view=source_view,
            dominant_clump=dominant_clump,
        )
        return maya_typed_success(
            "Created editable guide curve '{}' in cluster '{}'".format(created_curve, cluster_id),
            typed_result,
            prompt="Create the remaining cluster guides with the same cluster_id and display_color_rgb.",
        )
    except ImportError:
        _delete_curve_quietly(locals().get("cmds"), created_curve)
        return skill_error("Maya not available", "maya.cmds or maya.api.OpenMaya could not be imported")
    except ValueError as exc:
        _delete_curve_quietly(locals().get("cmds"), created_curve)
        return skill_error("Invalid guide curve input", str(exc))
    except Exception as exc:
        _delete_curve_quietly(locals().get("cmds"), created_curve)
        return skill_exception(exc, message="Failed to create guide curve")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_guide_curve`."""
    return create_guide_curve(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
