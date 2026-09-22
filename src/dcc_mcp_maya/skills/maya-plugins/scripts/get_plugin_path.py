"""Report the plug-in search path and resolve a plug-in name to a file."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.plugins import PLUGIN_PATH_ENV, PluginContractError, find_plugin_file, plugin_search_path


def get_plugin_path(plugin: Optional[str] = None) -> dict:
    """Report the search path, and optionally where a plug-in resolves to."""
    try:
        path = plugin_search_path()
        context = {
            "env_var": path["env_var"],
            "entries": path["entries"],
            "count": path["count"],
            "missing": path["missing"],
        }
        message = "{} has {} entr{}".format(PLUGIN_PATH_ENV, path["count"], "y" if path["count"] == 1 else "ies")
        if plugin:
            located = find_plugin_file(plugin)
            context["plugin"] = located["plugin"]
            context["found"] = located["found"]
            context["candidates"] = located["candidates"]
            message += "; {} {}".format(located["plugin"], "found" if located["found"] else "not found")
        if path["missing"]:
            context["suggestion"] = "{} search path entr{} do not exist; remove or fix {}.".format(
                len(path["missing"]),
                "y" if len(path["missing"]) == 1 else "ies",
                "it" if len(path["missing"]) == 1 else "them",
            )
        return maya_success(message, **context)
    except PluginContractError as exc:
        return maya_error(
            "Invalid search path request",
            str(exc),
            possible_solutions=["Pass a plug-in name to resolve, or omit it to list the path."],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to read the plug-in search path")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_plugin_path`."""
    return get_plugin_path(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
