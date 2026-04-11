"""Create a set-driven key relationship between a driver and driven attributes."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List

def set_driven_key(
    driver_attr: str,
    driven_attrs: List[str],
    driver_values: List[float],
    driven_values: List[List[float]],
    tangent_type: str = "linear",
) -> dict:
    """Create a set-driven key relationship between a driver and driven attrs.

    A set-driven key creates an animation curve so that when *driver_attr*
    reaches each value in *driver_values*, each driven attribute in
    *driven_attrs* takes the corresponding value in *driven_values*.

    Args:
        driver_attr: Full attribute path for the driver (e.g.
            ``"ctrl.rotateY"``).
        driven_attrs: List of full attribute paths for driven attrs (e.g.
            ``["joint1.translateX", "joint1.translateZ"]``).
        driver_values: List of driver values that define the key positions.
            Must have at least 1 entry.
        driven_values: 2-D list ``[per_driver_value][per_driven_attr]``.
            ``driven_values[i][j]`` is the value of ``driven_attrs[j]`` when
            ``driver_attr == driver_values[i]``.
        tangent_type: Tangent type for the keys — ``"linear"``, ``"smooth"``,
            ``"flat"``, or ``"step"``.  Default: ``"linear"``.

    Returns:
        ActionResultModel dict with ``context.driver_attr``,
        ``context.driven_attrs``, ``context.key_count``.
    """

    _VALID_TANGENTS = ("linear", "smooth", "flat", "step")

    if not driver_values:
        return maya_error(
            "driver_values cannot be empty",
            "Provide at least one driver value",
        )

    if len(driven_values) != len(driver_values):
        return maya_error(
            "Mismatched driver/driven value counts",
            "driven_values must have the same length as driver_values",
        )

    if tangent_type not in _VALID_TANGENTS:
        return maya_error(
            "Invalid tangent_type: {}".format(tangent_type),
            "Use one of: {}".format(", ".join(_VALID_TANGENTS)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        driver_obj = driver_attr.rsplit(".", 1)[0]
        if not cmds.objExists(driver_obj):
            return maya_error("Driver object not found: {}".format(driver_obj))

        for da in driven_attrs:
            da_obj = da.rsplit(".", 1)[0]
            if not cmds.objExists(da_obj):
                return maya_error("Driven object not found: {}".format(da_obj))

        keys_set = 0
        for i, drv_val in enumerate(driver_values):
            cmds.setAttr(driver_attr, drv_val)
            row = driven_values[i]
            for j, da in enumerate(driven_attrs):
                da_val = row[j] if j < len(row) else 0.0
                cmds.setAttr(da, da_val)
                cmds.setDrivenKeyframe(
                    da,
                    currentDriver=driver_attr,
                    inTangentType=tangent_type,
                    outTangentType=tangent_type,
                )
                keys_set += 1

        return maya_success(
            "Set driven key: '{}' drives {} attr(s) with {} key(s)".format(
                driver_attr, len(driven_attrs), len(driver_values)
            ),
            driver_attr=driver_attr,
            driven_attrs=driven_attrs,
            key_count=len(driver_values),
            keys_set=keys_set,
            tangent_type=tangent_type,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set driven key")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_driven_key`."""
    return set_driven_key(**kwargs)

if __name__ == "__main__":
    import json

    result = set_driven_key()
    print(json.dumps(result))
