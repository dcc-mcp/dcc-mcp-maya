"""Maya lighting actions — create, modify and query lights."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional

# Supported Maya light types and their corresponding command/node names
_LIGHT_TYPE_MAP = {
    "point": "pointLight",
    "spot": "spotLight",
    "directional": "directionalLight",
    "area": "areaLight",
    "ambient": "ambientLight",
}


def create_light(
    light_type: str = "point",
    name: Optional[str] = None,
    intensity: float = 1.0,
    color: Optional[List[float]] = None,
    position: Optional[List[float]] = None,
) -> dict:
    """Create a Maya light of the specified type.

    Args:
        light_type: One of ``"point"``, ``"spot"``, ``"directional"``,
            ``"area"``, ``"ambient"``.  Default: ``"point"``.
        name: Optional name for the light transform node.
        intensity: Initial light intensity.  Default: 1.0.
        color: RGB colour as ``[r, g, b]`` in 0-1 range.  Default: white.
        position: World-space position ``[x, y, z]``.  Default: [0, 0, 0].

    Returns:
        ActionResultModel dict with ``context.light_name`` and
        ``context.light_shape``.
    """

    lt = light_type.lower()
    if lt not in _LIGHT_TYPE_MAP:
        return maya_error(
            "Unsupported light type: {}".format(light_type),
            "Supported types: {}".format(", ".join(sorted(_LIGHT_TYPE_MAP))),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        create_cmd = getattr(cmds, _LIGHT_TYPE_MAP[lt])
        kwargs = {}
        if name:
            kwargs["name"] = name
        shape = create_cmd(**kwargs)
        # For directional/area/ambient cmds return shape; for point/spot they
        # return a list [shape, transform] or just the shape depending on version.
        if isinstance(shape, (list, tuple)):
            shape = shape[0]

        # Find the transform parent of the shape
        transform = cmds.listRelatives(shape, parent=True)
        transform = transform[0] if transform else shape

        # Apply intensity
        cmds.setAttr("{}.intensity".format(shape), intensity)

        # Apply colour
        r, g, b = (color[0], color[1], color[2]) if color and len(color) >= 3 else (1.0, 1.0, 1.0)
        cmds.setAttr("{}.color".format(shape), r, g, b, type="double3")

        # Apply position
        if position and len(position) >= 3:
            cmds.setAttr("{}.translate".format(transform), position[0], position[1], position[2], type="double3")

        return maya_success(
            "Created {} light '{}'".format(lt, transform),
            light_name=transform,
            light_shape=shape,
            light_type=lt,
            intensity=intensity,
            color=[r, g, b],
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create light")


def set_light_attribute(
    light_name: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute on a Maya light node.

    This function accepts either the transform or the shape name.  It will
    automatically resolve the shape node when needed.

    Common attributes: ``"intensity"``, ``"color"``, ``"coneAngle"`` (spot),
    ``"penumbraAngle"`` (spot), ``"dropoff"`` (spot), ``"shadowColor"``,
    ``"useDepthMapShadows"``.

    Args:
        light_name: Name of the light transform or shape.
        attribute: Attribute name (e.g. ``"intensity"``).
        value: New value.  Lists/tuples are expanded as ``double3`` vectors.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_name):
            return maya_error("Light not found: {}".format(light_name))

        # Try to resolve shape for light-specific attrs
        shapes = cmds.listRelatives(light_name, shapes=True) or []
        target = shapes[0] if shapes else light_name

        full_attr = "{}.{}".format(target, attribute)
        if not cmds.objExists(full_attr):
            # Attribute may be on transform instead
            full_attr = "{}.{}".format(light_name, attribute)
        if not cmds.objExists(full_attr):
            return maya_error("Attribute '{}' not found on '{}'".format(attribute, light_name))

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(full_attr, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        else:
            cmds.setAttr(full_attr, value)

        return maya_success(
            "Set {}.{} = {}".format(light_name, attribute, value),
            light_name=light_name,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set light attribute")


def list_lights(include_default: bool = False) -> dict:
    """List all lights in the current Maya scene.

    Args:
        include_default: If True, include the ``defaultLight`` which Maya creates
            internally.  Default: False.

    Returns:
        ActionResultModel dict with ``context.lights`` list of dicts containing
        ``name``, ``shape``, ``light_type``, ``intensity``, ``color``,
        ``visible``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        light_shapes = cmds.ls(type="light") or []
        # Also catch spotLight / pointLight / directionalLight / areaLight by hierarchy
        for extra_type in ("spotLight", "pointLight", "directionalLight", "areaLight", "ambientLight"):
            extra = cmds.ls(type=extra_type) or []
            for node in extra:
                if node not in light_shapes:
                    light_shapes.append(node)

        results = []
        for shape in light_shapes:
            if not include_default and shape == "defaultLight":
                continue
            transform_list = cmds.listRelatives(shape, parent=True) or [shape]
            transform = transform_list[0]
            try:
                intensity = cmds.getAttr("{}.intensity".format(shape))
            except Exception:
                intensity = None
            try:
                color_raw = cmds.getAttr("{}.color".format(shape))
                color = list(color_raw[0]) if color_raw else None
            except Exception:
                color = None
            try:
                visible = bool(cmds.getAttr("{}.visibility".format(transform)))
            except Exception:
                visible = True
            results.append(
                {
                    "name": transform,
                    "shape": shape,
                    "light_type": cmds.objectType(shape),
                    "intensity": intensity,
                    "color": color,
                    "visible": visible,
                }
            )

        return maya_success(
            "Found {} light(s)".format(len(results)),
            lights=results,
            count=len(results),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list lights")


def delete_light(light_name: str) -> dict:
    """Delete a light from the scene by transform name.

    Args:
        light_name: Name of the light transform to delete.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_name):
            return maya_error("Light not found: {}".format(light_name))

        node_type = cmds.objectType(light_name)
        # If it's a shape, delete its transform
        if node_type not in ("transform",):
            parents = cmds.listRelatives(light_name, parent=True)
            if parents:
                light_name = parents[0]

        cmds.delete(light_name)
        return maya_success(
            "Deleted light '{}'".format(light_name),
            light_name=light_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete light")
