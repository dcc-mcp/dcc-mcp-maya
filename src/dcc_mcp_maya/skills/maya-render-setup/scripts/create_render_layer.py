"""Create a renderSetup render layer."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError, load_render_setup
from dcc_mcp_maya.render_setup import create_render_layer as _create_render_layer


def create_render_layer(
    name: Optional[str] = None,
    renderable: bool = True,
    activate: bool = False,
) -> dict:
    """Create a renderSetup layer and optionally make it visible."""
    try:
        render_setup = load_render_setup()
        result = _create_render_layer(
            render_setup,
            name=name or "",
            renderable=renderable,
            activate=activate,
        )
        return maya_success(
            "Created render layer {}".format(result["created"]),
            layer=result["layer"],
            created=result["created"],
            renderable=bool(renderable),
            prompt=(
                "Add contents with create_render_collection, then override values with "
                "create_render_override. Switch to it with set_current_render_layer."
            ),
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid render layer request",
            str(exc),
            possible_solutions=[
                "Pass a unique name that no existing render layer uses.",
                "Use list_render_layers to see the layers already in the scene.",
                "Load the renderSetup plug-in if render setup is unavailable.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.app.renderSetup could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create render layer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_render_layer`."""
    return create_render_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
