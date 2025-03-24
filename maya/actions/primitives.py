"""Primitives creation actions for Maya.

This module provides actions for creating primitive objects in Maya.
"""


from dcc_mcp_core.models import ActionResultModel


def create_primitive(primitive_type: str, **kwargs) -> ActionResultModel:
    """Create a primitive object in Maya.

    Args:
        primitive_type: Type of primitive to create (cube, sphere, cylinder, cone, plane, torus)
        **kwargs: Additional arguments for the primitive creation command

    Returns:
        ActionResultModel with the result of the primitive creation

    """
    # Get Maya commands from context
    maya_client = kwargs.pop("_maya_rpyc_client", None)
    cmds = kwargs.pop("_maya_cmds", None)

    if not cmds:
        return ActionResultModel(
            success=False,
            message="创建几何体失败",
            error="Maya commands not available",
            prompt="请确保 Maya 已启动并且连接正常",
            context={},
        )

    # Map of primitive types to Maya commands
    primitive_commands = {
        "cube": cmds.polyCube,
        "sphere": cmds.polySphere,
        "cylinder": cmds.polyCylinder,
        "cone": cmds.polyCone,
        "plane": cmds.polyPlane,
        "torus": cmds.polyTorus,
    }

    # Check if the primitive type is supported
    if primitive_type not in primitive_commands:
        return ActionResultModel(
            success=False,
            message=f"不支持的几何体类型: {primitive_type}",
            error=f"Unsupported primitive type: {primitive_type}",
            prompt="请使用以下几何体类型之一: cube, sphere, cylinder, cone, plane, torus",
            context={"supported_types": list(primitive_commands.keys())},
        )

    try:
        # Create the primitive
        result = primitive_commands[primitive_type](**kwargs)

        # Return success result
        return ActionResultModel(
            success=True,
            message=f"成功创建 {primitive_type} 几何体",
            prompt=f"可以使用 cmds.select('{result[0]}') 选中该对象",
            error=None,
            context={"created_objects": result, "primitive_type": primitive_type, "parameters": kwargs},
        )
    except Exception as e:
        # Return error result
        return ActionResultModel(
            success=False,
            message=f"创建 {primitive_type} 几何体失败",
            error=str(e),
            prompt="请检查参数是否正确，或者查看 Maya 控制台获取更多信息",
            context={"primitive_type": primitive_type, "parameters": kwargs},
        )


def create_cube(width: float = 1.0, height: float = 1.0, depth: float = 1.0, **kwargs) -> ActionResultModel:
    """Create a cube in Maya.

    Args:
        width: Width of the cube (default: 1.0)
        height: Height of the cube (default: 1.0)
        depth: Depth of the cube (default: 1.0)
        **kwargs: Additional arguments for the polyCube command

    Returns:
        ActionResultModel with the result of the cube creation

    """
    # Add dimensions to kwargs
    kwargs["width"] = width
    kwargs["height"] = height
    kwargs["depth"] = depth

    return create_primitive("cube", **kwargs)


def create_sphere(radius: float = 1.0, **kwargs) -> ActionResultModel:
    """Create a sphere in Maya.

    Args:
        radius: Radius of the sphere (default: 1.0)
        **kwargs: Additional arguments for the polySphere command

    Returns:
        ActionResultModel with the result of the sphere creation

    """
    # Add radius to kwargs
    kwargs["radius"] = radius

    return create_primitive("sphere", **kwargs)
