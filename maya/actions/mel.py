"""MEL script execution actions for Maya.

This module provides actions for executing MEL scripts in Maya.
"""


from dcc_mcp_core.models import ActionResultModel


def execute_mel(script: str, **kwargs) -> ActionResultModel:
    """Execute a MEL script in Maya.

    Args:
        script: MEL script to execute
        **kwargs: Additional context parameters

    Returns:
        ActionResultModel with the result of the MEL script execution

    """
    # Get Maya client from context
    maya_client = kwargs.pop("_maya_rpyc_client", None)

    if not maya_client:
        return ActionResultModel(
            success=False,
            message="执行 MEL 脚本失败",
            error="Maya client not available",
            prompt="请确保 Maya 已启动并且连接正常",
            context={},
        )

    try:
        # Execute the MEL script
        result = maya_client.connection.modules.maya.mel.eval(script)

        # Return success result
        return ActionResultModel(
            success=True,
            message="成功执行 MEL 脚本",
            prompt="可以使用 get_scene_info 函数查看脚本执行后的场景状态",
            error=None,
            context={"script": script, "result": str(result) if result is not None else None},
        )
    except Exception as e:
        # Return error result
        return ActionResultModel(
            success=False,
            message="执行 MEL 脚本失败",
            error=str(e),
            prompt="请检查 MEL 脚本语法是否正确，或者查看 Maya 控制台获取更多信息",
            context={"script": script},
        )


def execute_command(command: str, *args, **kwargs) -> ActionResultModel:
    """Execute a Maya command.

    Args:
        command: Maya command to execute
        *args: Positional arguments for the command
        **kwargs: Keyword arguments for the command

    Returns:
        ActionResultModel with the result of the command execution

    """
    # Get Maya commands from context
    maya_context = kwargs.copy()
    maya_client = maya_context.pop("_maya_rpyc_client", None)
    cmds = maya_context.pop("_maya_cmds", None)

    if not cmds:
        return ActionResultModel(
            success=False,
            message="执行 Maya 命令失败",
            error="Maya commands not available",
            prompt="请确保 Maya 已启动并且连接正常",
            context={},
        )

    try:
        # Get the command function
        cmd_func = getattr(cmds, command, None)

        if not cmd_func:
            return ActionResultModel(
                success=False,
                message=f"未找到 Maya 命令: {command}",
                error=f"Command not found: {command}",
                prompt="请检查命令名称是否正确",
                context={},
            )

        # Execute the command
        result = cmd_func(*args, **maya_context)

        # Return success result
        return ActionResultModel(
            success=True,
            message=f"成功执行 Maya 命令: {command}",
            prompt="可以使用 get_scene_info 函数查看命令执行后的场景状态",
            error=None,
            context={"command": command, "args": args, "kwargs": maya_context, "result": result},
        )
    except Exception as e:
        # Return error result
        return ActionResultModel(
            success=False,
            message=f"执行 Maya 命令失败: {command}",
            error=str(e),
            prompt="请检查命令参数是否正确，或者查看 Maya 控制台获取更多信息",
            context={"command": command, "args": args, "kwargs": maya_context},
        )
