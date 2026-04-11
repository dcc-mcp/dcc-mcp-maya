"""List all lights in the scene, grouped by rig transform nodes."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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


def list_light_rigs() -> dict:
    """List all lights in the scene grouped by their parent rig transforms.

    Returns:
        ActionResultModel dict with ``context.rigs`` (dict mapping group name
        → list of light nodes) and ``context.total_lights``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        all_lights = []
        for ltype in _LIGHT_TYPES:
            try:
                found = cmds.ls(type=ltype) or []
                all_lights.extend(found)
            except Exception:
                pass

        rigs = {}  # type: dict
        ungrouped = []  # type: list

        for shape in all_lights:
            transform = (cmds.listRelatives(shape, parent=True) or [None])[0]
            if transform is None:
                ungrouped.append(shape)
                continue

            parent = (cmds.listRelatives(transform, parent=True) or [None])[0]
            group_key = parent if parent else "__ungrouped__"

            light_info = {
                "shape": shape,
                "transform": transform,
                "type": cmds.objectType(shape),
            }

            try:
                light_info["intensity"] = cmds.getAttr("{}.intensity".format(shape))
            except Exception:
                pass

            rigs.setdefault(group_key, []).append(light_info)

        return maya_success(
            "Found {} light(s) across {} rig group(s)".format(len(all_lights), len(rigs)),
            prompt="Use set_light_rig_intensity to adjust all lights in a rig group.",
            rigs=rigs,
            total_lights=len(all_lights),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list light rigs")


def main(**kwargs):
    return list_light_rigs(**kwargs)


if __name__ == "__main__":
    import json

    result = list_light_rigs()
    print(json.dumps(result))
