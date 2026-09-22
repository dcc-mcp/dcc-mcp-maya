"""Switch the active render layer (renderSetup or legacy)."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError, load_render_setup
from dcc_mcp_maya.render_setup import switch_legacy_render_layer as _switch_legacy
from dcc_mcp_maya.render_setup import switch_render_layer as _switch


def set_current_render_layer(
    name: Optional[str] = None,
    layer_system: str = "render_setup",
) -> dict:
    """Make a render layer the current one."""
    system = str(layer_system or "render_setup").strip().lower()
    if system not in ("render_setup", "legacy"):
        return maya_error(
            "Invalid layer system",
            "layer_system must be 'render_setup' or 'legacy', got {!r}".format(layer_system),
            possible_solutions=[
                "Use layer_system='render_setup' for layers created by create_render_layer.",
                "Use layer_system='legacy' for pre-2017 renderLayer nodes.",
            ],
        )
    try:
        if system == "legacy":
            import maya.cmds as cmds  # noqa: PLC0415

            result = _switch_legacy(cmds, name or "")
            if not result["applied"]:
                # Maya silently ignores legacy switches in batch sessions.
                return maya_error(
                    "Legacy render layer switch did not take effect",
                    "Requested {} but the current layer is still {}. Maya ignores legacy "
                    "render layer switches in batch / headless sessions.".format(
                        result["requested"], result["current"]
                    ),
                    possible_solutions=[
                        "Run this in an interactive Maya session.",
                        "Use layer_system='render_setup', which is the supported path.",
                    ],
                )
            return maya_success(
                "Switched to legacy render layer {}".format(result["requested"]),
                requested=result["requested"],
                current=result["current"],
                applied=result["applied"],
                layer_system="legacy",
            )

        render_setup = load_render_setup()
        result = _switch(render_setup, name or "")
        return maya_success(
            "Switched to render layer {}".format(result["layer"]),
            layer=result["layer"],
            visible_layer=result["visible_layer"],
            layer_system="render_setup",
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid render layer switch",
            str(exc),
            possible_solutions=[
                "Use list_render_layers to get the exact layer names.",
                "For legacy nodes pass layer_system='legacy'.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to switch render layer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_current_render_layer`."""
    return set_current_render_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
