"""Unload a Maya plug-in, refusing when Maya reports it cannot be unloaded."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.plugins import PluginContractError
from dcc_mcp_maya.plugins import unload_plugin as _unload_plugin


def unload_plugin(plugin: Optional[str] = None, force: bool = False) -> dict:
    """Unload a plug-in."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _unload_plugin(cmds, plugin=plugin or "", force=force)
        return maya_success(
            "Unloaded plug-in {}".format(result["plugin"]),
            plugin=result["plugin"],
            loaded=False,
            forced=result["forced"],
        )
    except PluginContractError as exc:
        return maya_error(
            "Plug-in could not be unloaded",
            str(exc),
            possible_solutions=[
                "Use list_plugins to see which plug-ins are currently loaded.",
                "Pass force=true only if you accept losing dependent nodes.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to unload plug-in")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`unload_plugin`."""
    return unload_plugin(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
