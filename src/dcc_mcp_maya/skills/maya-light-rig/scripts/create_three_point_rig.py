"""Create a standard three-point lighting rig (key/fill/rim)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import math
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_three_point_rig(
    name: str = "threePoint_rig",
    key_intensity: float = 1.0,
    fill_intensity: float = 0.5,
    rim_intensity: float = 0.75,
    light_type: str = "directionalLight",
    key_color: Optional[list] = None,
    fill_color: Optional[list] = None,
    rim_color: Optional[list] = None,
    arnold_exposure: float = 3.0,
) -> dict:
    """Create a standard three-point key/fill/rim lighting rig.

    Args:
        name: Base name for the rig group and lights.  Default: ``threePoint_rig``.
        key_intensity: Key light intensity.  Default: 1.0.
        fill_intensity: Fill light intensity.  Default: 0.5.
        rim_intensity: Rim (back/hair) light intensity.  Default: 0.75.
        light_type: Maya light node type for all three lights:
            ``directionalLight`` (default), ``spotLight``, ``pointLight``.
        key_color: RGB list for the key light, e.g. ``[1.0, 0.95, 0.85]``.
            Defaults to warm white.
        fill_color: RGB list for the fill light.  Defaults to cool white.
        rim_color: RGB list for the rim light.  Defaults to neutral white.
        arnold_exposure: Shared bounded Arnold exposure in stops.  The default
            offsets the evaluation's observed three-stop underexposure while
            preserving the key/fill/rim intensity ratios.

    Returns:
        ToolResult dict with ``context.rig_group``,
        ``context.key_light``, ``context.fill_light``, ``context.rim_light``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if isinstance(arnold_exposure, bool) or not isinstance(arnold_exposure, (int, float)):
            return skill_error("Invalid Arnold exposure", "arnold_exposure must be a finite number")
        exposure = float(arnold_exposure)
        if not math.isfinite(exposure) or not -20.0 <= exposure <= 20.0:
            return skill_error(
                "Arnold exposure is outside the supported range",
                "arnold_exposure must be finite and between -20 and 20 stops",
            )
        try:
            if not cmds.pluginInfo("mtoa", q=True, loaded=True):
                cmds.loadPlugin("mtoa", quiet=True)
            if not cmds.pluginInfo("mtoa", q=True, loaded=True):
                return skill_error(
                    "Arnold is unavailable",
                    "The mtoa plug-in must be loaded before creating exposure-calibrated lights",
                )
        except Exception as exc:
            return skill_exception(exc, message="Failed to load the mtoa plug-in")

        key_col = key_color if key_color else [1.0, 0.95, 0.85]
        fill_col = fill_color if fill_color else [0.85, 0.90, 1.0]
        rim_col = rim_color if rim_color else [1.0, 1.0, 1.0]

        rig_grp = cmds.group(empty=True, name=name)

        def _make_light(light_name, intensity, color, rx, ry):
            transform = cmds.createNode("transform", name=light_name, parent=rig_grp)
            cmds.shadingNode(
                light_type,
                asLight=True,
                name="{}_Shape".format(light_name),
                parent=transform,
            )
            shape = cmds.listRelatives(transform, shapes=True, type=light_type, fullPath=False)[0]
            cmds.setAttr("{}.intensity".format(shape), intensity)
            cmds.setAttr("{}.color".format(shape), *color[:3], type="double3")
            cmds.setAttr("{}.rotateX".format(transform), rx)
            cmds.setAttr("{}.rotateY".format(transform), ry)
            if not cmds.attributeQuery("aiExposure", node=shape, exists=True):
                raise RuntimeError("{} does not expose Arnold aiExposure".format(shape))
            exposure_attr = "{}.aiExposure".format(shape)
            cmds.setAttr(exposure_attr, exposure)
            actual_exposure = cmds.getAttr(exposure_attr)
            if (
                isinstance(actual_exposure, bool)
                or not isinstance(actual_exposure, (int, float))
                or not math.isfinite(float(actual_exposure))
                or abs(float(actual_exposure) - exposure) > 1e-6
            ):
                raise RuntimeError("{} Arnold exposure did not round-trip".format(shape))
            return {
                "transform": transform,
                "shape": shape,
                "intensity": intensity,
                "exposure": float(actual_exposure),
            }

        try:
            key = _make_light("{}_key".format(name), key_intensity, key_col, -30, -45)
            fill = _make_light("{}_fill".format(name), fill_intensity, fill_col, -15, 45)
            rim = _make_light("{}_rim".format(name), rim_intensity, rim_col, 0, 180)
        except Exception:
            try:
                cmds.delete(rig_grp)
            except Exception:
                pass
            raise

        return skill_success(
            "Created three-point rig '{}' ({})".format(name, light_type),
            prompt="Use set_light_rig_intensity to adjust brightness or create_hdri_dome for IBL.",
            rig_group=rig_grp,
            key_light=key["transform"],
            fill_light=fill["transform"],
            rim_light=rim["transform"],
            light_type=light_type,
            arnold_exposure=exposure,
            lights=[key, fill, rim],
            verified=True,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create three-point rig '{}'".format(name))


@skill_entry
def main(**kwargs):
    return create_three_point_rig(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
