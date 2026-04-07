"""MEL script actions for Maya MCP."""

# Import built-in modules
import logging

# Import third-party modules
from dcc_mcp_core import ActionResultModel

logger = logging.getLogger(__name__)


def execute_mel(script: str) -> ActionResultModel:
    """Execute a MEL script string.

    Args:
        script: MEL script to execute.

    Returns:
        ActionResultModel with the result.

    """
    import maya.mel as mel
    try:
        result = mel.eval(script)
        return ActionResultModel(
            success=True,
            message="MEL script executed",
            context={"result": result},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def run_mel_file(file_path: str) -> ActionResultModel:
    """Execute a MEL script file.

    Args:
        file_path: Path to the .mel file.

    Returns:
        ActionResultModel with the result.

    """
    import maya.mel as mel
    import os
    try:
        if not os.path.exists(file_path):
            return ActionResultModel(
                success=False,
                message=f"MEL file not found: {file_path}",
                error="FileNotFoundError",
            )
        result = mel.eval(f'source "{file_path.replace(chr(92), "/")}"')
        return ActionResultModel(
            success=True,
            message=f"MEL file executed: {file_path}",
            context={"result": result},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def register_actions(registry) -> None:
    """Register all MEL actions with the given ActionRegistry.

    Args:
        registry: ActionRegistry instance from dcc-mcp-core.

    """
    for func in [execute_mel, run_mel_file]:
        try:
            registry.register(func.__name__, func)
        except Exception as e:
            logger.warning(f"Failed to register action '{func.__name__}': {e}")
