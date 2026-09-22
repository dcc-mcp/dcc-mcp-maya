"""Create an override inside a renderSetup collection."""

from __future__ import annotations

from typing import Any, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import OVERRIDE_TYPES, RenderSetupContractError, load_render_setup
from dcc_mcp_maya.render_setup import create_override as _create_override


def create_render_override(
    layer: Optional[str] = None,
    collection: Optional[str] = None,
    attribute: Optional[str] = None,
    value: Any = None,
    override_type: str = "absolute",
) -> dict:
    """Override an attribute for everything a collection selects."""
    try:
        render_setup = load_render_setup()
        result = _create_override(
            render_setup,
            layer=layer or "",
            collection=collection or "",
            attribute=attribute or "",
            value=value,
            override_type=override_type,
        )
        return maya_success(
            "Created {} override on {} in {}/{}".format(
                result["override_type"], result["attribute"], result["layer"], result["collection"]
            ),
            **result,
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid render override request",
            str(exc),
            possible_solutions=[
                "override_type must be one of: " + ", ".join(OVERRIDE_TYPES),
                "attribute is 'node.attribute' (e.g. hero.visibility) or a bare attribute applied to every member.",
                "Create the layer and collection first, and check names with list_render_layers.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.app.renderSetup could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create render override")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_render_override`."""
    return create_render_override(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
