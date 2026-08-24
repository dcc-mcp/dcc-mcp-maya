"""Set one bounded batch of keys and verify Maya's curve values."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import math
import re
from numbers import Real
from typing import Dict, List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._mutation import MayaUndoChunk

ANIM_CURVES_SCHEMA = "dcc-mcp/anim-curves@1"
MAX_OBJECTS = 32
MAX_KEYS = 512
MAX_WRITES = 4096
MAX_SNAPSHOT_KEYS = 65536
_ATTRIBUTE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TANGENT_TYPES = {
    "auto",
    "clamped",
    "fast",
    "fixed",
    "flat",
    "linear",
    "plateau",
    "slow",
    "smooth",
    "spline",
    "step",
    "stepnext",
}
_FPS_BY_UNIT = {
    "game": 15.0,
    "film": 24.0,
    "pal": 25.0,
    "ntsc": 30.0,
    "show": 48.0,
    "palf": 50.0,
    "ntscf": 60.0,
}
_INFINITY_BY_VALUE = {
    0: "constant",
    1: "linear",
    2: "cycle",
    3: "cycle_relative",
    4: "oscillate",
}


class _LayeredCurveError(RuntimeError):
    pass


def _fps(cmds) -> float:
    unit = str(cmds.currentUnit(query=True, time=True) or "film")
    if unit in _FPS_BY_UNIT:
        return _FPS_BY_UNIT[unit]
    if unit.endswith("fps"):
        try:
            value = float(unit[:-3])
            if math.isfinite(value) and value > 0.0:
                return value
        except ValueError:
            pass
    raise ValueError("Unsupported Maya time unit: {}".format(unit))


def _validated_keys(keys: List[Dict]) -> List[Dict]:
    if not isinstance(keys, list) or not 1 <= len(keys) <= MAX_KEYS:
        raise ValueError("keys must contain between 1 and {} entries".format(MAX_KEYS))
    normalized = []
    seen_times = set()
    for index, row in enumerate(keys):
        if not isinstance(row, dict) or set(row) - {"time", "value", "in_tangent", "out_tangent"}:
            raise ValueError("keys[{}] has unsupported fields".format(index))
        if "time" not in row or "value" not in row:
            raise ValueError("keys[{}] requires time and value".format(index))
        if any(isinstance(row[field], bool) or not isinstance(row[field], Real) for field in ("time", "value")):
            raise ValueError("keys[{}] time and value must be numbers".format(index))
        time = float(row["time"])
        value = float(row["value"])
        if not math.isfinite(time) or not math.isfinite(value):
            raise ValueError("keys[{}] time and value must be finite".format(index))
        if time in seen_times:
            raise ValueError("duplicate key time: {}".format(time))
        seen_times.add(time)
        in_tangent = row.get("in_tangent")
        out_tangent = row.get("out_tangent")
        for label, tangent in (("in_tangent", in_tangent), ("out_tangent", out_tangent)):
            if tangent is not None and tangent not in _TANGENT_TYPES:
                raise ValueError("keys[{}].{} is unsupported".format(index, label))
        normalized.append(
            {
                "time": time,
                "value": value,
                "in_tangent": in_tangent,
                "out_tangent": out_tangent,
            }
        )
    return normalized


def _read_values(cmds, plug: str) -> Dict[float, float]:
    times = cmds.keyframe(plug, query=True, timeChange=True) or []
    values = cmds.keyframe(plug, query=True, valueChange=True) or []
    if len(times) != len(values):
        raise RuntimeError("Maya returned misaligned key times and values for {}".format(plug))
    output = {}
    for time, value in zip(times, values):
        numeric_time = float(time)
        numeric_value = float(value)
        if not math.isfinite(numeric_time) or not math.isfinite(numeric_value):
            raise RuntimeError("Maya returned a non-finite key for {}".format(plug))
        if numeric_time in output:
            raise RuntimeError("Maya returned duplicate key times for {}".format(plug))
        output[numeric_time] = numeric_value
    return output


def _native_key_count(cmds, plug: str) -> int:
    raw = cmds.keyframe(plug, query=True, keyframeCount=True)
    if isinstance(raw, bool):
        raise RuntimeError("Maya returned an invalid key count for {}".format(plug))
    try:
        count = int(raw)
    except (TypeError, ValueError):
        raise RuntimeError("Maya returned an invalid key count for {}".format(plug))
    if count < 0 or count != raw:
        raise RuntimeError("Maya returned an invalid key count for {}".format(plug))
    return count


def _curve_preflight(cmds, plug: str):
    curves = [str(item) for item in (cmds.keyframe(plug, query=True, name=True) or [])]
    if len(curves) > 1:
        raise _LayeredCurveError("{} has multiple animation curves".format(plug))
    if not curves:
        return None, 0
    key_count = _native_key_count(cmds, plug)
    if key_count > MAX_SNAPSHOT_KEYS:
        raise ValueError("{} exceeds the {} snapshot-key limit".format(plug, MAX_SNAPSHOT_KEYS))
    return curves[0], key_count


def _curve_snapshot(cmds, plug: str, curve, expected_key_count: int) -> Dict:
    if curve is None:
        return {"curve": None, "keys": ()}
    times = cmds.keyframe(plug, query=True, timeChange=True) or []
    values = cmds.keyframe(plug, query=True, valueChange=True) or []
    in_tangents = cmds.keyTangent(plug, query=True, inTangentType=True) or []
    out_tangents = cmds.keyTangent(plug, query=True, outTangentType=True) or []
    in_angles = cmds.keyTangent(plug, query=True, inAngle=True) or []
    out_angles = cmds.keyTangent(plug, query=True, outAngle=True) or []
    in_weights = cmds.keyTangent(plug, query=True, inWeight=True) or []
    out_weights = cmds.keyTangent(plug, query=True, outWeight=True) or []
    tangent_locks = cmds.keyTangent(plug, query=True, lock=True) or []
    weight_locks = cmds.keyTangent(plug, query=True, weightLock=True) or []
    arrays = (
        times,
        values,
        in_tangents,
        out_tangents,
        in_angles,
        out_angles,
        in_weights,
        out_weights,
        tangent_locks,
        weight_locks,
    )
    if len({len(items) for items in arrays}) != 1 or len(times) != expected_key_count:
        raise RuntimeError("Maya returned misaligned curve arrays for {}".format(plug))
    weighted_raw = cmds.keyTangent(plug, query=True, weightedTangents=True)
    weighted_values = list(weighted_raw) if isinstance(weighted_raw, (list, tuple)) else [weighted_raw]
    if not weighted_values or any(value not in (True, False, 0, 1) for value in weighted_values):
        raise RuntimeError("Maya returned invalid weighted tangent state for {}".format(plug))
    if any(bool(value) != bool(weighted_values[0]) for value in weighted_values):
        raise RuntimeError("Maya returned inconsistent weighted tangent state for {}".format(plug))
    weighted_tangents = bool(weighted_values[0])

    keys = []
    for (
        time,
        value,
        in_tangent,
        out_tangent,
        in_angle,
        out_angle,
        in_weight,
        out_weight,
        tangent_lock,
        weight_lock,
    ) in zip(*arrays):
        numeric_time = float(time)
        numeric_value = float(value)
        numeric_tangent_values = tuple(float(item) for item in (in_angle, out_angle, in_weight, out_weight))
        if (
            not math.isfinite(numeric_time)
            or not math.isfinite(numeric_value)
            or any(not math.isfinite(item) for item in numeric_tangent_values)
        ):
            raise RuntimeError("Maya returned a non-finite key for {}".format(plug))
        if tangent_lock not in (True, False, 0, 1) or weight_lock not in (True, False, 0, 1):
            raise RuntimeError("Maya returned invalid tangent lock state for {}".format(plug))
        keys.append(
            (
                numeric_time,
                numeric_value,
                str(in_tangent),
                str(out_tangent),
                numeric_tangent_values[0],
                numeric_tangent_values[1],
                numeric_tangent_values[2],
                numeric_tangent_values[3],
                bool(tangent_lock),
                bool(weight_lock),
            )
        )
    return {
        "curve": curve,
        "keys": tuple(keys),
        "weighted_tangents": weighted_tangents,
        "pre_infinity": _read_infinity(cmds, curve, "preInfinity"),
        "post_infinity": _read_infinity(cmds, curve, "postInfinity"),
    }


def _curve_batch_matches(cmds, snapshots: Dict[str, Dict]) -> bool:
    for plug, snapshot in snapshots.items():
        curve, key_count = _curve_preflight(cmds, plug)
        if _curve_snapshot(cmds, plug, curve, key_count) != snapshot:
            return False
    return True


def _read_tangent(cmds, plug: str, time: float, query_flag: str) -> str:
    kwargs = {"query": True, "time": (time, time), query_flag: True}
    values = cmds.keyTangent(plug, **kwargs) or []
    if not values:
        raise RuntimeError("Maya returned no {} readback for {} at {}".format(query_flag, plug, time))
    return str(values[0])


def _read_infinity(cmds, curve: str, attribute: str) -> str:
    raw = cmds.getAttr("{}.{}".format(curve, attribute))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise RuntimeError("Maya returned an invalid {} for {}".format(attribute, curve))
    if value not in _INFINITY_BY_VALUE:
        raise RuntimeError("Maya returned an unknown {} for {}".format(attribute, curve))
    return _INFINITY_BY_VALUE[value]


def set_keyframes(objects: List[str], attribute: str, keys: List[Dict]) -> dict:
    """Set the same typed curve on multiple objects and verify every key."""
    transaction = None
    before_by_plug = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_OBJECTS:
            return skill_error(
                "Invalid object batch",
                "objects must contain between 1 and {} names".format(MAX_OBJECTS),
            )
        if any(not isinstance(item, str) for item in objects):
            return skill_error("Invalid object batch", "object names must be strings")
        object_names = list(objects)
        if any(not item or len(item) > 256 for item in object_names) or len(set(object_names)) != len(object_names):
            return skill_error("Invalid object batch", "object names must be unique non-empty strings")
        if not isinstance(attribute, str) or not _ATTRIBUTE_RE.match(attribute):
            return skill_error("Invalid attribute", "attribute must be one Maya attribute name")
        try:
            normalized_keys = _validated_keys(keys)
        except (TypeError, ValueError) as exc:
            return skill_error("Invalid key batch", str(exc))
        if len(object_names) * len(normalized_keys) > MAX_WRITES:
            return skill_error(
                "Key batch is too large",
                "objects x keys must not exceed {} writes".format(MAX_WRITES),
            )

        plugs = ["{}.{}".format(object_name, attribute) for object_name in object_names]
        missing = [
            plug
            for object_name, plug in zip(object_names, plugs)
            if not cmds.objExists(object_name) or not cmds.objExists(plug)
        ]
        if missing:
            return skill_error("Animation targets were not found", "Missing Maya plugs: {}".format(", ".join(missing)))

        preflights = {}
        snapshot_key_count = 0
        for plug in plugs:
            try:
                curve, key_count = _curve_preflight(cmds, plug)
            except _LayeredCurveError as exc:
                return skill_error(
                    "Layered animation target is ambiguous",
                    "{}; select one layer before batching".format(exc),
                )
            except ValueError as exc:
                return skill_error("Animation snapshot is too large", str(exc))
            preflights[plug] = (curve, key_count)
            snapshot_key_count += key_count
            if snapshot_key_count > MAX_SNAPSHOT_KEYS:
                return skill_error(
                    "Animation snapshot is too large",
                    "existing key count exceeds {}".format(MAX_SNAPSHOT_KEYS),
                )

        before_by_plug = {
            plug: _curve_snapshot(cmds, plug, curve, key_count) for plug, (curve, key_count) in preflights.items()
        }

        frame_rate = _fps(cmds)
        transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
        transaction.begin()

        for plug in plugs:
            for key in normalized_keys:
                cmds.setKeyframe(plug, time=key["time"], value=key["value"])
                tangent_kwargs = {}
                if key["in_tangent"] is not None:
                    tangent_kwargs["inTangentType"] = key["in_tangent"]
                if key["out_tangent"] is not None:
                    tangent_kwargs["outTangentType"] = key["out_tangent"]
                if tangent_kwargs:
                    cmds.keyTangent(plug, edit=True, time=(key["time"], key["time"]), **tangent_kwargs)

        curves = []
        for plug in plugs:
            curve = before_by_plug[plug]["curve"]
            if curve is None:
                created = [str(item) for item in (cmds.keyframe(plug, query=True, name=True) or [])]
                if len(created) != 1:
                    receipt = transaction.rollback(lambda: _curve_batch_matches(cmds, before_by_plug))
                    return skill_error(
                        "Animation curve readback failed",
                        "{} did not resolve to exactly one animation curve after the write".format(plug),
                        **receipt,
                    )
                curve = created[0]
            values_by_time = _read_values(cmds, plug)
            read_keys = []
            for key in normalized_keys:
                actual_value = values_by_time.get(key["time"])
                if actual_value is None or abs(actual_value - key["value"]) > 1e-6:
                    receipt = transaction.rollback(lambda: _curve_batch_matches(cmds, before_by_plug))
                    return skill_error(
                        "Animation curve readback failed",
                        "{} at {} did not match the requested value".format(plug, key["time"]),
                        target=plug,
                        time=key["time"],
                        expected_value=key["value"],
                        actual_value=actual_value,
                        **receipt,
                    )
                requested_in = key["in_tangent"]
                requested_out = key["out_tangent"]
                actual_in = _read_tangent(cmds, plug, key["time"], "inTangentType")
                actual_out = _read_tangent(cmds, plug, key["time"], "outTangentType")
                if requested_in is not None:
                    if actual_in != requested_in:
                        receipt = transaction.rollback(lambda: _curve_batch_matches(cmds, before_by_plug))
                        return skill_error(
                            "Animation tangent readback failed",
                            "{} input tangent did not match".format(plug),
                            **receipt,
                        )
                if requested_out is not None:
                    if actual_out != requested_out:
                        receipt = transaction.rollback(lambda: _curve_batch_matches(cmds, before_by_plug))
                        return skill_error(
                            "Animation tangent readback failed",
                            "{} output tangent did not match".format(plug),
                            **receipt,
                        )
                read_keys.append(
                    {
                        "t": key["time"],
                        "v": actual_value,
                        "in": actual_in,
                        "out": actual_out,
                    }
                )
            curves.append(
                {
                    "target": plug,
                    "keys": read_keys,
                    "pre_infinity": _read_infinity(cmds, curve, "preInfinity"),
                    "post_infinity": _read_infinity(cmds, curve, "postInfinity"),
                    "key_count": len(read_keys),
                }
            )

        transaction.commit()
        return skill_success(
            "Set and verified {} keys across {} animation curves".format(
                len(object_names) * len(normalized_keys), len(object_names)
            ),
            schema=ANIM_CURVES_SCHEMA,
            fps=frame_rate,
            curves=curves,
            curve_count=len(curves),
            verified_key_count=len(object_names) * len(normalized_keys),
            prompt="Use get_anim_curves to inspect full tangent and infinity state.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        receipt = {}
        if transaction is not None and before_by_plug is not None:
            receipt = transaction.rollback(lambda: _curve_batch_matches(cmds, before_by_plug))
        return skill_exception(exc, message="Failed to set the animation key batch", **receipt)


@skill_entry
def main(**kwargs) -> dict:
    return set_keyframes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
