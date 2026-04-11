"""List all lights in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_LIGHT_SHAPE_TYPES = [
    "directionalLight",
    "pointLight",
    "spotLight",
    "areaLight",
    "ambientLight",
    "volumeLight",
    # Arnold
    "aiAreaLight",
    "aiSkyDomeLight",
    "aiMeshLight",
    # VRay
    "VRayLightSphereShape",
    "VRayLightDomeShape",
]


def list_lights() -> dict:
    """List all lights in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.lights`` — list of dicts
        with ``transform``, ``shape``, ``type``, and ``intensity``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        shapes = cmds.ls(type=_LIGHT_SHAPE_TYPES) or []
        lights = []
        for shape in shapes:
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or [shape]
            transform = parents[0]
            ltype = cmds.objectType(shape)
            try:
                intensity = cmds.getAttr("{}.intensity".format(shape))
            except Exception:
                intensity = None
            lights.append(
                {
                    "transform": transform,
                    "shape": shape,
                    "type": ltype,
                    "intensity": intensity,
                }
            )

        return maya_success(
            "Found {} light(s) in the scene".format(len(lights)),
            prompt="Use create_light to add a light or set_light_attribute to modify one.",
            lights=lights,
            count=len(lights),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list lights")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_lights`."""
    return list_lights(**kwargs)


if __name__ == "__main__":
    import json

    result = list_lights()
    print(json.dumps(result))
