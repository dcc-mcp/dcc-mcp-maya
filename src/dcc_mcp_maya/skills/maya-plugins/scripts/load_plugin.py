"""Load a Maya plug-in, with an actionable error when it cannot be found."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.plugins import PLUGIN_PATH_ENV, PluginContractError
from dcc_mcp_maya.plugins import load_plugin as _load_plugin


def load_plugin(plugin: Optional[str] = None, autoload: bool = False) -> dict:
    """Load a plug-in and optionally remember it for future sessions."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _load_plugin(cmds, plugin=plugin or "", autoload=autoload)
        record = result["record"]
        return maya_success(
            "Loaded plug-in {}".format(result["plugin"]),
            plugin=result["plugin"],
            loaded=result["loaded"],
            was_loaded=result["was_loaded"],
            autoload=result["autoload"],
            version=record.get("version"),
            path=record.get("path"),
            vendor=record.get("vendor"),
            prompt="Use list_plugins to confirm load state across the scene.",
        )
    except PluginContractError as exc:
        return maya_error(
            "Plug-in could not be loaded",
            str(exc),
            possible_solutions=[
                "Check the plug-in name; it is case-sensitive.",
                "Add the plug-in directory to {} or install the plug-in.".format(PLUGIN_PATH_ENV),
                "Use diagnose_plugin for a path / load-state breakdown.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to load plug-in")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`load_plugin`."""
    return load_plugin(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
