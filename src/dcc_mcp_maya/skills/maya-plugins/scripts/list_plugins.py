"""List Maya plug-ins with load state and metadata."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.plugins import PluginContractError
from dcc_mcp_maya.plugins import list_plugins as _list_plugins


def list_plugins(
    pattern: str = "",
    loaded_only: bool = False,
    limit: int = 200,
    search_path: dict = None,
) -> dict:
    """List plug-ins Maya can address, loaded or not."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _list_plugins(
            cmds,
            pattern=pattern,
            loaded_only=loaded_only,
            limit=limit,
            search_path=search_path,
        )
        return maya_success(
            "Listed {} plug-in(s) ({} loaded)".format(result["count"], result["loaded_count"]),
            plugins=result["plugins"],
            count=result["count"],
            total_matches=result["total_matches"],
            loaded_count=result["loaded_count"],
            truncated=result["truncated"],
            pattern=result["pattern"],
            loaded_only=result["loaded_only"],
            prompt=(
                "Version, path and vendor are only reported for loaded plug-ins; "
                "use diagnose_plugin or load_plugin to inspect an unloaded one."
            ),
        )
    except PluginContractError as exc:
        return maya_error(
            "Invalid plug-in listing request",
            str(exc),
            possible_solutions=[
                "limit must be >= 1.",
                "Use pattern to filter by name substring.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list plug-ins")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_plugins`."""
    return list_plugins(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
