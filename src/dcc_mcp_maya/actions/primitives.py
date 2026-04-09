"""Maya polygon primitive creation and transform actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_sphere(radius: float = 1.0, name: Optional[str] = None) -> dict:
    """Create a polygon sphere.

    Args:
        radius: Sphere radius. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"radius": radius, "subdivisionsAxis": 20, "subdivisionsHeight": 20}
        result = cmds.polySphere(**kwargs)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            f"Created sphere: {obj}",
            object_name=obj,
            radius=radius,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_sphere failed")
        return error_result("Failed to create sphere", str(exc)).to_dict()


def create_cube(
    width: float = 1.0,
    height: float = 1.0,
    depth: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon cube.

    Args:
        width: Cube width. Default: 1.0.
        height: Cube height. Default: 1.0.
        depth: Cube depth. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyCube(width=width, height=height, depth=depth)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            f"Created cube: {obj}",
            object_name=obj,
            width=width,
            height=height,
            depth=depth,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_cube failed")
        return error_result("Failed to create cube", str(exc)).to_dict()


def create_cylinder(
    radius: float = 1.0,
    height: float = 2.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon cylinder.

    Args:
        radius: Cylinder radius. Default: 1.0.
        height: Cylinder height. Default: 2.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyCylinder(radius=radius, height=height, subdivisionsAxis=20)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            f"Created cylinder: {obj}",
            object_name=obj,
            radius=radius,
            height=height,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_cylinder failed")
        return error_result("Failed to create cylinder", str(exc)).to_dict()


def create_plane(
    width: float = 1.0,
    height: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon plane.

    Args:
        width: Plane width. Default: 1.0.
        height: Plane height. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyPlane(width=width, height=height, subdivisionsX=1, subdivisionsY=1)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            "Created plane: {}".format(obj),
            object_name=obj,
            width=width,
            height=height,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_plane failed")
        return error_result("Failed to create plane", str(exc)).to_dict()


def get_transform(object_name: str) -> dict:
    """Get the translate/rotate/scale of an object.

    Args:
        object_name: Name of the object to query.

    Returns:
        ActionResultModel dict with translate, rotate, scale lists.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        translate = list(cmds.getAttr("{}.translate".format(object_name))[0])
        rotate = list(cmds.getAttr("{}.rotate".format(object_name))[0])
        scale = list(cmds.getAttr("{}.scale".format(object_name))[0])
        return success_result(
            "Transform of {}".format(object_name),
            object_name=object_name,
            translate=translate,
            rotate=rotate,
            scale=scale,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_transform failed")
        return error_result("Failed to get transform of {}".format(object_name), str(exc)).to_dict()


def rename_object(object_name: str, new_name: str) -> dict:
    """Rename a Maya object.

    Args:
        object_name: Current name of the object.
        new_name: New name to assign.

    Returns:
        ActionResultModel dict with ``context.object_name`` (new name).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        result = cmds.rename(object_name, new_name)
        return success_result(
            "Renamed '{}' to '{}'".format(object_name, result),
            old_name=object_name,
            object_name=result,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("rename_object failed")
        return error_result("Failed to rename {}".format(object_name), str(exc)).to_dict()


def delete_objects(objects: List[str]) -> dict:
    """Delete objects from the Maya scene.

    Args:
        objects: List of object names to delete.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return success_result("No objects to delete").to_dict()
        existing = cmds.ls(objects) or []
        if existing:
            cmds.delete(existing)
        return success_result(
            f"Deleted {len(existing)} objects",
            deleted=existing,
            requested=objects,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_objects failed")
        return error_result("Failed to delete objects", str(exc)).to_dict()


def set_transform(
    object_name: str,
    translate: Optional[List[float]] = None,
    rotate: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
) -> dict:
    """Set the translate/rotate/scale of an object.

    Args:
        object_name: Name of the object to transform.
        translate: [tx, ty, tz] in scene units.  None = no change.
        rotate: [rx, ry, rz] in degrees.  None = no change.
        scale: [sx, sy, sz].  None = no change.

    Returns:
        ActionResultModel dict with applied transform values.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                f"Object not found: {object_name}",
                f"'{object_name}' does not exist in the scene",
            ).to_dict()

        applied: dict = {}
        if translate is not None and len(translate) == 3:
            cmds.setAttr(f"{object_name}.translate", *translate, type="double3")
            applied["translate"] = translate
        if rotate is not None and len(rotate) == 3:
            cmds.setAttr(f"{object_name}.rotate", *rotate, type="double3")
            applied["rotate"] = rotate
        if scale is not None and len(scale) == 3:
            cmds.setAttr(f"{object_name}.scale", *scale, type="double3")
            applied["scale"] = scale

        return success_result(
            f"Transform applied to {object_name}",
            object_name=object_name,
            **applied,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_transform failed")
        return error_result(f"Failed to set transform on {object_name}", str(exc)).to_dict()


_ACTIONS = [
    ("create_sphere", "Create a polygon sphere", "geometry", ["create", "mesh", "sphere"]),
    ("create_cube", "Create a polygon cube", "geometry", ["create", "mesh", "cube"]),
    ("create_cylinder", "Create a polygon cylinder", "geometry", ["create", "mesh", "cylinder"]),
    ("create_plane", "Create a polygon plane", "geometry", ["create", "mesh", "plane"]),
    ("delete_objects", "Delete objects from the scene", "geometry", ["delete", "mesh"]),
    ("set_transform", "Set translate/rotate/scale on an object", "geometry", ["transform", "move"]),
    ("get_transform", "Get translate/rotate/scale of an object", "geometry", ["transform", "query"]),
    ("rename_object", "Rename an object in the scene", "geometry", ["rename", "object"]),
]
