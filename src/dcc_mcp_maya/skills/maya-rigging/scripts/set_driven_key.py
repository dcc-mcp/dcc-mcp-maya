"""Create a set-driven key relationship between a driver and driven attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists


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
        ToolResult dict with ``context.driver_attr``,
        ``context.driven_attrs``, ``context.key_count``.
    """

    _VALID_TANGENTS = ("linear", "smooth", "flat", "step")

    if not driver_values:
        return skill_error(
            "driver_values cannot be empty",
            "Provide at least one driver value",
        )

    if len(driven_values) != len(driver_values):
        return skill_error(
            "Mismatched driver/driven value counts",
            "driven_values must have the same length as driver_values",
        )

    if tangent_type not in _VALID_TANGENTS:
        return skill_error(
            "Invalid tangent_type: {}".format(tangent_type),
            "Use one of: {}".format(", ".join(_VALID_TANGENTS)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        driver_obj = driver_attr.rsplit(".", 1)[0]
        err = validate_node_exists(cmds, driver_obj)
        if err:
            return err

        driven_objs = list({da.rsplit(".", 1)[0] for da in driven_attrs})
        err = batch_validate_nodes(cmds, driven_objs)
        if err:
            return err

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

        return skill_success(
            "Set driven key: '{}' drives {} attr(s) with {} key(s)".format(
                driver_attr, len(driven_attrs), len(driver_values)
            ),
            driver_attr=driver_attr,
            driven_attrs=driven_attrs,
            key_count=len(driver_values),
            keys_set=keys_set,
            tangent_type=tangent_type,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set driven key")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_driven_key`."""
    return set_driven_key(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
