"""Verify Maya modeling operation evidence without mutating the scene."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_OPERATIONS = ("loft", "lathe", "extrude", "bevel", "array", "mirror", "pivot", "cleanup", "uv")
_HISTORY_TYPES = {
    "loft": ("loft",),
    "lathe": ("revolve",),
    "extrude": ("polyExtrudeFace", "polyExtrudeEdge", "extrude"),
    "bevel": ("polyBevel", "polyBevel2", "polyBevel3"),
    "mirror": ("polyMirrorFace",),
}
_PARAMETERS = {
    "loft": ("degree", "uniform", "close", "sectionSpans"),
    "lathe": ("segments", "startSweep", "endSweep", "axis"),
    "extrude": ("localTranslateX", "localTranslateY", "localTranslateZ", "thickness", "keepFacesTogether"),
    "bevel": ("offset", "segments", "autoFit", "mergeVertices"),
    "mirror": ("axis", "axisDirection", "cutMesh", "mergeMode", "mergeThreshold", "axisPos"),
}


def _compare(actual: Any, expected: Any) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=1e-5, abs_tol=1e-5)
    return actual == expected


def _read_history(cmds: Any, object_name: str, operation: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        history = cmds.listHistory(object_name, pruneDagObjects=True)
    except Exception as exc:
        return [], str(exc)
    if not isinstance(history, (list, tuple)):
        return [], "Maya returned an invalid history list"
    evidence: List[Dict[str, Any]] = []
    for node in history:
        try:
            node_type = str(cmds.nodeType(node))
        except Exception:
            continue
        if node_type not in _HISTORY_TYPES.get(operation, ()):
            continue
        parameters: Dict[str, Any] = {}
        for parameter in _PARAMETERS.get(operation, ()):
            try:
                value = cmds.getAttr("{}.{}".format(node, parameter))
            except Exception:
                continue
            if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], (list, tuple)):
                value = value[0]
            parameters[parameter] = value
        evidence.append({"node": str(node), "type": node_type, "parameters": parameters})
    return evidence, None


def _check_pivot(
    cmds: Any, object_name: str, expected: Dict[str, Any]
) -> Tuple[Optional[bool], Dict[str, Any], Optional[str]]:
    try:
        values = cmds.xform(object_name, query=True, worldSpace=True, pivots=True)
        if not isinstance(values, (list, tuple)) or len(values) < 6:
            return None, {}, "Maya did not return both pivots"
        actual = {
            "rotate_pivot": [float(value) for value in values[:3]],
            "scale_pivot": [float(value) for value in values[3:6]],
        }
        requested = expected.get("position")
        if requested is None:
            return True, actual, None
        passed = all(_compare(actual["rotate_pivot"][index], requested[index]) for index in range(3))
        passed = passed and all(_compare(actual["scale_pivot"][index], requested[index]) for index in range(3))
        return passed, actual, None
    except Exception as exc:
        return None, {}, str(exc)


def _check_uv(
    cmds: Any, object_name: str, expected: Dict[str, Any]
) -> Tuple[Optional[bool], Dict[str, Any], Optional[str]]:
    try:
        current = cmds.polyUVSet(object_name, query=True, currentUVSet=True) or []
        uv_count = int(cmds.polyEvaluate(object_name, uvcoord=True) or 0)
        actual = {"uv_set": str(current[0]) if current else None, "uv_count": uv_count}
        minimum = int(expected.get("min_uv_count", 1))
        return uv_count >= minimum, actual, None
    except Exception as exc:
        return None, {}, str(exc)


def _check_cleanup(
    cmds: Any, object_name: str, expected: Dict[str, Any]
) -> Tuple[Optional[bool], Dict[str, Any], Optional[str]]:
    try:
        findings = []
        for flag in ("nonManifoldVertices", "nonManifoldEdges"):
            result = cmds.polyInfo(object_name, **{flag: True})
            if result:
                findings.extend(result if isinstance(result, (list, tuple)) else [str(result)])
        return not findings, {"non_manifold_findings": findings}, None
    except Exception as exc:
        return None, {}, str(exc)


def _check_array(
    cmds: Any, object_name: str, instance_names: Optional[Sequence[str]], expected: Dict[str, Any]
) -> Tuple[Optional[bool], Dict[str, Any], Optional[str]]:
    names = list(instance_names or expected.get("instance_names") or [])
    if names:
        missing = [name for name in names if not cmds.objExists(name)]
        return (
            not missing,
            {"instance_names": names, "missing": missing, "verified_count": len(names) - len(missing)},
            None,
        )
    count = expected.get("count")
    if count is None:
        return None, {}, "array verification needs instance_names or expected.count"
    return (
        None,
        {"expected_count": int(count), "source_object": object_name},
        "array count needs explicit instance_names readback",
    )


def verify_modeling_operation(
    object_name: str,
    operation: str,
    expected: Optional[Dict[str, Any]] = None,
    instance_names: Optional[List[str]] = None,
) -> dict:
    """Return pass/fail/unknown native operation evidence."""
    if operation not in _OPERATIONS:
        return skill_error("Invalid modeling operation", "operation must be one of {}".format(", ".join(_OPERATIONS)))
    expected = dict(expected or {})
    try:
        import maya.cmds as cmds

        if not cmds.objExists(object_name):
            return skill_error("Modeling object not found", "Maya object does not exist: {}".format(object_name))
        if operation == "pivot":
            passed, evidence, error = _check_pivot(cmds, object_name, expected)
        elif operation == "uv":
            passed, evidence, error = _check_uv(cmds, object_name, expected)
        elif operation == "cleanup":
            passed, evidence, error = _check_cleanup(cmds, object_name, expected)
        elif operation == "array":
            passed, evidence, error = _check_array(cmds, object_name, instance_names, expected)
        else:
            history, error = _read_history(cmds, object_name, operation)
            evidence = {"native_history": history}
            if error:
                passed = None
            elif not history:
                passed = None
                evidence["error"] = "Maya returned no matching native history node"
            else:
                passed = True
                for key, expected_value in expected.items():
                    observed = [item["parameters"].get(key) for item in history if key in item["parameters"]]
                    if not observed or not any(_compare(value, expected_value) for value in observed):
                        passed = False
                        evidence.setdefault("mismatches", []).append(
                            {"parameter": key, "expected": expected_value, "observed": observed}
                        )
        status = "unknown" if passed is None else ("pass" if passed else "fail")
        if error:
            evidence["error"] = error
        return skill_success(
            "Maya {} operation verification {}".format(operation, status),
            status=status,
            passed=status == "pass",
            operation=operation,
            object_name=object_name,
            evidence=evidence,
            expected=expected,
            actionable_error=error,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to verify Maya modeling operation")


@skill_entry
def main(**kwargs) -> dict:
    return verify_modeling_operation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
