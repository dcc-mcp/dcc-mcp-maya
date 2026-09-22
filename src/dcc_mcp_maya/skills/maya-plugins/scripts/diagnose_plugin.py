"""Explain why a plug-in is or is not usable."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.plugins import PluginContractError
from dcc_mcp_maya.plugins import diagnose_plugin as _diagnose


def diagnose_plugin(plugin: Optional[str] = None) -> dict:
    """Report a plug-in's search path, load state and any problems."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _diagnose(cmds, plugin=plugin or "")
        return maya_success(
            "{} is {}".format(result["plugin"], "usable" if result["healthy"] else "not usable"),
            plugin=result["plugin"],
            known=result["known"],
            loaded=result["loaded"],
            registered=result["registered"],
            file_found=result["file_found"],
            candidates=result["candidates"],
            record=result["record"],
            search_path=result["search_path"],
            problems=result["problems"],
            suggestions=result["suggestions"],
            healthy=result["healthy"],
        )
    except PluginContractError as exc:
        return maya_error(
            "Invalid plug-in diagnosis request",
            str(exc),
            possible_solutions=["Pass a plug-in name, e.g. diagnose_plugin(plugin='mtoa')."],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to diagnose plug-in")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`diagnose_plugin`."""
    return diagnose_plugin(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
