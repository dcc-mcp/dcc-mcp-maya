"""Return Maya version, scene path, and basic stats."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _safe_get_attr(cmds, attr: str):
    try:
        return cmds.getAttr(attr)
    except Exception:
        return None


def _plugin_loaded(cmds, plugin_name: str) -> bool:
    try:
        return bool(cmds.pluginInfo(plugin_name, q=True, loaded=True))
    except Exception:
        return False


def _plugin_version(cmds, plugin_name: str):
    try:
        return cmds.pluginInfo(plugin_name, q=True, version=True)
    except Exception:
        return None


def get_session_info() -> dict:
    """Return Maya version, scene path, and basic stats.

    Returns:
        ToolResult dict with version, scene, fps information.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # ``cmds.ls`` boolean flags (``dag``, ``dagObjects``, …) must run on
        # Maya's UI thread.  The sidecar / inline HTTP executor path can invoke
        # this script from a worker thread, where those flags raise
        # ``TypeError: … boolean parameter``.  ``type=`` filters are safe
        # off-thread; transform count is a stable proxy for scene size.
        transforms = cmds.ls(type="transform") or []
        mtoa_loaded = _plugin_loaded(cmds, "mtoa")
        info = {
            "maya_version": cmds.about(version=True),
            "api_version": cmds.about(apiVersion=True),
            "python_version": sys.version,
            "scene_file": cmds.file(query=True, sceneName=True) or "<unsaved>",
            "scene_modified": cmds.file(query=True, modified=True),
            "fps": cmds.currentUnit(query=True, time=True),
            "up_axis": cmds.upAxis(query=True, axis=True),
            "object_count": len(transforms),
            "current_renderer": _safe_get_attr(cmds, "defaultRenderGlobals.currentRenderer"),
            "mtoa_loaded": mtoa_loaded,
            "mtoa_version": _plugin_version(cmds, "mtoa") if mtoa_loaded else None,
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
