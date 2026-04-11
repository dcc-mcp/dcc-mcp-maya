"""Open a Maya scene file."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

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
        return skill_success(
            f"Opened scene: {file_path}",
            file_path=file_path,
            prompt="Use get_scene_info to inspect the scene contents.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message=f"Failed to open {file_path}")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`open_scene`."""
    return open_scene(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
