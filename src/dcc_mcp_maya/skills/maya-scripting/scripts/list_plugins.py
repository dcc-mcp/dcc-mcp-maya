"""List loaded Maya plug-ins and lightweight plug-in metadata."""

from __future__ import annotations

from typing import Any, Dict, List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def _safe_plugin_info(cmds: Any, plugin: str, flag: str, default: Any = None) -> Any:
    try:
        return cmds.pluginInfo(plugin, query=True, **{flag: True})
    except Exception:  # noqa: BLE001 - plug-in metadata flags vary across Maya versions
        return default


def _plugin_record(cmds: Any, plugin: str, include_details: bool) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "name": plugin,
        "loaded": bool(_safe_plugin_info(cmds, plugin, "loaded", False)),
        "autoload": bool(_safe_plugin_info(cmds, plugin, "autoload", False)),
        "registered": bool(_safe_plugin_info(cmds, plugin, "registered", False)),
    }
    if include_details:
        for field, flag in (
            ("path", "path"),
            ("version", "version"),
            ("vendor", "vendor"),
            ("api_version", "apiVersion"),
            ("unload_ok", "unloadOk"),
        ):
            value = _safe_plugin_info(cmds, plugin, flag)
            if value not in (None, ""):
                record[field] = value
    return record


def list_plugins(pattern: str = "", include_details: bool = True, limit: int = 200) -> dict:
    """List Maya plug-ins, optionally filtered by case-insensitive substring."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        raw_plugins = cmds.pluginInfo(query=True, listPlugins=True) or []
        plugins = sorted(str(plugin) for plugin in raw_plugins)
        if pattern:
            needle = str(pattern).lower()
            plugins = [plugin for plugin in plugins if needle in plugin.lower()]

        max_count = max(1, int(limit))
        selected = plugins[:max_count]
        records: List[Dict[str, Any]] = [
            _plugin_record(cmds, plugin, include_details=bool(include_details)) for plugin in selected
        ]
        return maya_success(
            "Listed {} Maya plug-in(s)".format(len(records)),
            plugins=records,
            count=len(records),
            total_matches=len(plugins),
            truncated=len(plugins) > len(records),
            pattern=str(pattern or ""),
            include_details=bool(include_details),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list Maya plug-ins")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_plugins`."""
    return list_plugins(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
