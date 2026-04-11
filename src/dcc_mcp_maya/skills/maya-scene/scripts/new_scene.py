"""Create a new empty Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def new_scene(force: bool = False) -> dict:
    """Create a new Maya scene.

    Args:
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(new=True, force=force)
        return maya_success("New scene created")
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create new scene")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`new_scene`."""
    return new_scene(**kwargs)

if __name__ == "__main__":
    import json

    result = new_scene()
    print(json.dumps(result))
