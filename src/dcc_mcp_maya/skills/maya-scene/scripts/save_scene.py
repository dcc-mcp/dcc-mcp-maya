"""Save the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def save_scene(file_path: Optional[str] = None, file_type: str = "mayaBinary") -> dict:
    """Save the current Maya scene.

    Args:
        file_path: Destination path.  If None, saves to the current file path.
        file_type: ``"mayaBinary"`` (default) or ``"mayaAscii"``.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if file_path:
            cmds.file(rename=file_path)
        saved = cmds.file(save=True, type=file_type)
        return maya_success(
            f"Scene saved to {saved}",
            file_path=saved,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to save scene")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`save_scene`."""
    return save_scene(**kwargs)

if __name__ == "__main__":
    import json

    result = save_scene()
    print(json.dumps(result))
