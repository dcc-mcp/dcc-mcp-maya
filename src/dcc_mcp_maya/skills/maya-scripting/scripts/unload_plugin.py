"""Unload a Maya plug-in via ``cmds.unloadPlugin``."""

from __future__ import annotations

from typing import Any, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def _plugin_loaded(cmds: Any, plugin: str) -> bool:
    try:
        return bool(cmds.pluginInfo(plugin, query=True, loaded=True))
    except Exception:  # noqa: BLE001 - Maya raises when the plug-in name is unknown
        return False


def _set_autoload(cmds: Any, plugin: str, enabled: Optional[bool]) -> Optional[bool]:
    if enabled is None:
        try:
            return bool(cmds.pluginInfo(plugin, query=True, autoload=True))
        except Exception:  # noqa: BLE001
            return None
    cmds.pluginInfo(plugin, edit=True, autoload=bool(enabled))
    try:
        return bool(cmds.pluginInfo(plugin, query=True, autoload=True))
    except Exception:  # noqa: BLE001
        return bool(enabled)


def unload_plugin(
    plugin: str,
    force: bool = False,
    remove_autoload: bool = False,
    not_loaded_ok: bool = True,
) -> dict:
    """Unload a Maya plug-in and optionally clear its autoload preference."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        plugin_name = str(plugin or "").strip()
        if not plugin_name:
            return maya_error(
                "Invalid plugin",
                "plugin must be a non-empty plug-in name.",
                possible_solutions=["Pass the plug-in name reported by list_plugins."],
            )

        loaded_before = _plugin_loaded(cmds, plugin_name)
        if remove_autoload:
            autoload = _set_autoload(cmds, plugin_name, False)
        else:
            autoload = _set_autoload(cmds, plugin_name, None)

        if not loaded_before:
            if not not_loaded_ok:
                return maya_error(
                    "Maya plug-in is not loaded",
                    "{} is not currently loaded.".format(plugin_name),
                    plugin=plugin_name,
                    loaded=False,
                    autoload=autoload,
                )
            return maya_success(
                "Maya plug-in already unloaded",
                plugin=plugin_name,
                loaded=False,
                loaded_before=False,
                autoload=autoload,
                remove_autoload=bool(remove_autoload),
            )

        cmds.unloadPlugin(plugin_name, force=bool(force))
        loaded = _plugin_loaded(cmds, plugin_name)
        return maya_success(
            "Unloaded Maya plug-in: {}".format(plugin_name),
            plugin=plugin_name,
            loaded=loaded,
            loaded_before=loaded_before,
            force=bool(force),
            autoload=autoload,
            remove_autoload=bool(remove_autoload),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to unload Maya plug-in")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`unload_plugin`."""
    return unload_plugin(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
