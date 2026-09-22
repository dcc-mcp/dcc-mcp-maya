"""List renderSetup layers and legacy renderLayer nodes."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError, load_render_setup
from dcc_mcp_maya.render_setup import list_legacy_render_layers as _list_legacy
from dcc_mcp_maya.render_setup import list_render_layers as _list_layers


def list_render_layers(
    include_default: bool = True,
    include_legacy: bool = True,
) -> dict:
    """Report renderSetup layers, the visible layer, and legacy layers."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        render_setup = load_render_setup()
        result = _list_layers(render_setup, include_default=include_default)
        context = {
            "layers": result["layers"],
            "count": result["count"],
            "default_layer": result["default_layer"],
            "visible_layer": result["visible_layer"],
        }
        if include_legacy:
            legacy = _list_legacy(cmds)
            context["legacy_layers"] = legacy["layers"]
            context["legacy_current"] = legacy["current"]
            context["legacy_count"] = legacy["count"]
        return maya_success(
            "Found {} render setup layer(s)".format(result["count"]),
            **context,
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Render setup is unavailable",
            str(exc),
            possible_solutions=[
                "Load the renderSetup plug-in: cmds.loadPlugin('renderSetup').",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list render layers")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_render_layers`."""
    return list_render_layers(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
