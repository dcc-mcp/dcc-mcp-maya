"""Return Maya version, scene path, and basic stats."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_session_info() -> dict:
    """Return Maya version, scene path, and basic stats.

    Returns:
        ActionResultModel dict with version, scene, fps information.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        info = {
            "maya_version": cmds.about(version=True),
            "api_version": cmds.about(apiVersion=True),
            "python_version": sys.version,
            "scene_file": cmds.file(query=True, sceneName=True) or "<unsaved>",
            "scene_modified": cmds.file(query=True, modified=True),
            "fps": cmds.currentUnit(query=True, time=True),
            "up_axis": cmds.upAxis(query=True, axis=True),
            "object_count": len(cmds.ls(dag=True) or []),
        }
        return skill_success(
            "Maya session info", **info, prompt="Check the result with list_scene or use related actions to continue."
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get session info")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_session_info`."""
    return get_session_info(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
