"""Load a Maya plug-in via ``cmds.loadPlugin``."""

from __future__ import annotations

from typing import Any, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def _plugin_loaded(cmds: Any, plugin: str) -> bool:
    try:
        return bool(cmds.pluginInfo(plugin, query=True, loaded=True))
    except Exception:  # noqa: BLE001 - Maya raises when the plug-in name is unknown
        return False


def _plugin_autoload(cmds: Any, plugin: str) -> Optional[bool]:
    try:
        return bool(cmds.pluginInfo(plugin, query=True, autoload=True))
    except Exception:  # noqa: BLE001
        return None


def _set_autoload(cmds: Any, plugin: str, enabled: Optional[bool]) -> Optional[bool]:
    if enabled is None:
        return _plugin_autoload(cmds, plugin)
    cmds.pluginInfo(plugin, edit=True, autoload=bool(enabled))
    return _plugin_autoload(cmds, plugin)


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def load_plugin(
    plugin: str,
    quiet: bool = True,
    set_autoload: Optional[bool] = None,
    already_loaded_ok: bool = True,
) -> dict:
    """Load a Maya plug-in and optionally set its autoload preference."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        plugin_name = str(plugin or "").strip()
        if not plugin_name:
            return maya_error(
                "Invalid plugin",
                "plugin must be a non-empty plug-in name or path.",
                possible_solutions=["Pass a value such as 'fbxmaya' or a plug-in file path."],
            )

        loaded_before = _plugin_loaded(cmds, plugin_name)
        loaded_plugins: List[str] = []
        if loaded_before:
            if not already_loaded_ok:
                return maya_error(
                    "Maya plug-in is already loaded",
                    "{} is already loaded.".format(plugin_name),
                    plugin=plugin_name,
                    loaded=True,
                )
        else:
            loaded_plugins = _as_list(cmds.loadPlugin(plugin_name, quiet=bool(quiet)))

        autoload = _set_autoload(cmds, plugin_name, set_autoload)
        loaded = _plugin_loaded(cmds, plugin_name)
        return maya_success(
            "Loaded Maya plug-in: {}".format(plugin_name) if not loaded_before else "Maya plug-in already loaded",
            plugin=plugin_name,
            loaded=loaded,
            loaded_before=loaded_before,
            loaded_plugins=loaded_plugins,
            autoload=autoload,
            quiet=bool(quiet),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to load Maya plug-in")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`load_plugin`."""
    return load_plugin(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
