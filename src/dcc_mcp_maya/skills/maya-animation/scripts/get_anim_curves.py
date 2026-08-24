"""Read bounded Maya animation curves in the shared public shape."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import math
from typing import Dict, List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

ANIM_CURVES_SCHEMA = "dcc-mcp/anim-curves@1"
MAX_TARGETS = 128
MAX_CURVES = 256
MAX_KEYS_PER_CURVE = 4096
MAX_TOTAL_KEYS = 65536
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


def _fps(cmds) -> float:
    unit = str(cmds.currentUnit(query=True, time=True) or "film")
    if unit in _FPS_BY_UNIT:
        return _FPS_BY_UNIT[unit]
    if unit.endswith("fps"):
        value = float(unit[:-3])
        if math.isfinite(value) and value > 0.0:
            return value
    raise ValueError("Unsupported Maya time unit: {}".format(unit))


def _infinity_name(value) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError("Maya returned an invalid infinity mode: {}".format(value))
    if number not in _INFINITY_BY_VALUE:
        raise ValueError("Maya returned an unknown infinity mode: {}".format(number))
    return _INFINITY_BY_VALUE[number]


def _curve_row(cmds, curve: str, target: str) -> Dict:
    times = cmds.keyframe(curve, query=True, timeChange=True) or []
    values = cmds.keyframe(curve, query=True, valueChange=True) or []
    in_tangents = cmds.keyTangent(curve, query=True, inTangentType=True) or []
    out_tangents = cmds.keyTangent(curve, query=True, outTangentType=True) or []
    lengths = {len(times), len(values), len(in_tangents), len(out_tangents)}
    if len(lengths) != 1:
        raise RuntimeError("Maya returned misaligned curve arrays for {}".format(curve))
    keys = []
    for time, value, in_tangent, out_tangent in zip(times, values, in_tangents, out_tangents):
        numeric_time = float(time)
        numeric_value = float(value)
        if not math.isfinite(numeric_time) or not math.isfinite(numeric_value):
            raise RuntimeError("Maya returned a non-finite key for {}".format(curve))
        keys.append(
            {
                "t": numeric_time,
                "v": numeric_value,
                "in": str(in_tangent),
                "out": str(out_tangent),
            }
        )
    if len(keys) > MAX_KEYS_PER_CURVE:
        raise ValueError("Animation curve {} exceeds the {} key limit".format(curve, MAX_KEYS_PER_CURVE))
    return {
        "target": target,
        "keys": keys,
        "pre_infinity": _infinity_name(cmds.getAttr("{}.preInfinity".format(curve))),
        "post_infinity": _infinity_name(cmds.getAttr("{}.postInfinity".format(curve))),
        "key_count": len(keys),
    }


def get_anim_curves(targets: List[str]) -> dict:
    """Return values, tangents, infinity modes, and counts for explicit plugs."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_TARGETS:
            return skill_error(
                "Invalid animation targets",
                "targets must contain between 1 and {} plugs".format(MAX_TARGETS),
            )
        if any(not isinstance(item, str) for item in targets):
            return skill_error("Invalid animation targets", "targets must be strings")
        target_names = list(targets)
        if len(set(target_names)) != len(target_names) or any(
            not target or len(target) > 385 or "." not in target for target in target_names
        ):
            return skill_error("Invalid animation targets", "targets must be unique Maya node.attribute plugs")
        missing = [target for target in target_names if not cmds.objExists(target)]
        if missing:
            return skill_error("Animation targets were not found", "Missing Maya plugs: {}".format(", ".join(missing)))

        curve_targets = []
        for target in target_names:
            curve_names = [str(item) for item in (cmds.keyframe(target, query=True, name=True) or [])]
            if not curve_names:
                return skill_error("Animation curve not found", "{} has no animation curve".format(target))
            curve_targets.extend((curve, target) for curve in curve_names)
        if len(curve_targets) > MAX_CURVES:
            return skill_error("Too many animation curves", "curve count exceeds {}".format(MAX_CURVES))

        curves = []
        total_keys = 0
        for curve, target in curve_targets:
            row = _curve_row(cmds, curve, target)
            total_keys += row["key_count"]
            if total_keys > MAX_TOTAL_KEYS:
                return skill_error(
                    "Too many animation keys",
                    "key count exceeds {}".format(MAX_TOTAL_KEYS),
                )
            curves.append(row)
        return skill_success(
            "Read {} animation curve(s)".format(len(curves)),
            schema=ANIM_CURVES_SCHEMA,
            fps=_fps(cmds),
            curves=curves,
            curve_count=len(curves),
            total_key_count=total_keys,
            prompt="Use set_keyframes for bounded edits or export_animation_curves for Maya-native archival.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to read animation curves")


@skill_entry
def main(**kwargs) -> dict:
    return get_anim_curves(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
