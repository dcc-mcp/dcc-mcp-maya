"""Scale intensity of all lights within a named rig group."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

logger = logging.getLogger(__name__)

_LIGHT_TYPES = [
    "directionalLight",
    "pointLight",
    "spotLight",
    "areaLight",
    "ambientLight",
    "volumeLight",
    "aiSkyDomeLight",
    "aiAreaLight",
    "aiMeshLight",
    "aiPhotometricLight",
]


def set_light_rig_intensity(
    rig_group: str,
    intensity: float,
    multiply: bool = False,
) -> dict:
    """Scale intensity of all lights parented under a rig group.

    Args:
        rig_group: Name of the rig group transform node.
        intensity: New intensity value (absolute) or multiplier when
            ``multiply=True``.
        multiply: If True, multiply the current intensity by ``intensity``
            instead of setting an absolute value.  Default: False.

    Returns:
        ActionResultModel dict with ``context.updated_lights`` and
        ``context.rig_group``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, rig_group)
        if err:
            return err

        descendants = cmds.listRelatives(rig_group, allDescendents=True, type="shape") or []
        light_shapes = [n for n in descendants if cmds.objectType(n) in _LIGHT_TYPES]

        if not light_shapes:
            return skill_error(
                "No lights found under: {}".format(rig_group),
                "The group '{}' contains no light shape nodes".format(rig_group),
            )

        updated = []
        for shape in light_shapes:
            try:
                if multiply:
                    current = cmds.getAttr("{}.intensity".format(shape))
                    new_val = current * intensity
                else:
                    new_val = intensity
                cmds.setAttr("{}.intensity".format(shape), new_val)
                updated.append({"shape": shape, "intensity": new_val})
            except Exception as exc:
                logger.warning("Could not set intensity on %s: %s", shape, exc)

        return skill_success(
            "{} {} light(s) in rig '{}'".format(
                "Scaled" if multiply else "Set intensity of",
                len(updated),
                rig_group,
            ),
            prompt="Use list_light_rigs to review intensity values across all rigs.",
            rig_group=rig_group,
            updated_lights=updated,
            light_count=len(updated),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set intensity for rig '{}'".format(rig_group))


@skill_entry
def main(**kwargs):
    return set_light_rig_intensity(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
