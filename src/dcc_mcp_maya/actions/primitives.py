"""Primitive creation actions for Maya MCP."""

# Import built-in modules
import logging

# Import third-party modules
from dcc_mcp_core import ActionResultModel

logger = logging.getLogger(__name__)


def create_sphere(radius: float = 1.0, name: str = "") -> ActionResultModel:
    """Create a polygon sphere.

    Args:
        radius: Sphere radius (default 1.0).
        name: Optional name for the created object.

    Returns:
        ActionResultModel with the created object name.

    """
    import maya.cmds as cmds
    try:
        kwargs: dict = {"radius": radius}
        if name:
            kwargs["name"] = name
        result = cmds.polySphere(**kwargs)
        return ActionResultModel(
            success=True,
            message="Sphere created",
            context={"transform": result[0], "shape": result[1]},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def create_cube(width: float = 1.0, height: float = 1.0, depth: float = 1.0, name: str = "") -> ActionResultModel:
    """Create a polygon cube.

    Args:
        width: Cube width (default 1.0).
        height: Cube height (default 1.0).
        depth: Cube depth (default 1.0).
        name: Optional name for the created object.

    Returns:
        ActionResultModel with the created object name.

    """
    import maya.cmds as cmds
    try:
        kwargs: dict = {"width": width, "height": height, "depth": depth}
        if name:
            kwargs["name"] = name
        result = cmds.polyCube(**kwargs)
        return ActionResultModel(
            success=True,
            message="Cube created",
            context={"transform": result[0], "shape": result[1]},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def create_cylinder(radius: float = 1.0, height: float = 2.0, name: str = "") -> ActionResultModel:
    """Create a polygon cylinder.

    Args:
        radius: Cylinder radius (default 1.0).
        height: Cylinder height (default 2.0).
        name: Optional name for the created object.

    Returns:
        ActionResultModel with the created object name.

    """
    import maya.cmds as cmds
    try:
        kwargs: dict = {"radius": radius, "height": height}
        if name:
            kwargs["name"] = name
        result = cmds.polyCylinder(**kwargs)
        return ActionResultModel(
            success=True,
            message="Cylinder created",
            context={"transform": result[0], "shape": result[1]},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def delete_objects(objects: list) -> ActionResultModel:
    """Delete objects from the Maya scene.

    Args:
        objects: List of object names to delete.

    Returns:
        ActionResultModel indicating success.

    """
    import maya.cmds as cmds
    try:
        if not objects:
            return ActionResultModel(success=True, message="No objects to delete")
        cmds.delete(objects)
        return ActionResultModel(
            success=True,
            message=f"Deleted {len(objects)} objects",
            context={"deleted": objects},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def set_transform(
    object_name: str,
    translate: tuple = None,
    rotate: tuple = None,
    scale: tuple = None,
) -> ActionResultModel:
    """Set transform attributes on a Maya object.

    Args:
        object_name: Name of the object to transform.
        translate: (x, y, z) translation values.
        rotate: (x, y, z) rotation values in degrees.
        scale: (x, y, z) scale values.

    Returns:
        ActionResultModel indicating success.

    """
    import maya.cmds as cmds
    try:
        if translate is not None:
            cmds.setAttr(f"{object_name}.translate", *translate, type="double3")
        if rotate is not None:
            cmds.setAttr(f"{object_name}.rotate", *rotate, type="double3")
        if scale is not None:
            cmds.setAttr(f"{object_name}.scale", *scale, type="double3")
        return ActionResultModel(
            success=True,
            message=f"Transform set on '{object_name}'",
            context={"object": object_name},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def register_actions(registry) -> None:
    """Register all primitive actions with the given ActionRegistry.

    Args:
        registry: ActionRegistry instance from dcc-mcp-core.

    """
    for func in [create_sphere, create_cube, create_cylinder, delete_objects, set_transform]:
        try:
            registry.register(func.__name__, func)
        except Exception as e:
            logger.warning(f"Failed to register action '{func.__name__}': {e}")
