"""Open a Maya scene file."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def open_scene(file_path: str, force: bool = False) -> dict:
    """Open a Maya scene file.

    Args:
        file_path: Path to the .ma / .mb file.
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(file_path, open=True, force=force)
        return maya_success(
            f"Opened scene: {file_path}",
            file_path=file_path,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, f"Failed to open {file_path}")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`open_scene`."""
    return open_scene(**kwargs)

if __name__ == "__main__":
    import json

    result = open_scene()
    print(json.dumps(result))
