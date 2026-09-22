"""Create or replace a renderSetup collection's contents."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError, load_render_setup
from dcc_mcp_maya.render_setup import create_collection as _create_collection
from dcc_mcp_maya.render_setup import set_collection_members as _set_members


def create_render_collection(
    layer: Optional[str] = None,
    name: Optional[str] = None,
    members: Optional[List[str]] = None,
    pattern: Optional[str] = None,
    replace: bool = False,
) -> dict:
    """Create a collection in a layer, or replace an existing collection's contents."""
    try:
        render_setup = load_render_setup()
        if replace:
            result = _set_members(
                render_setup,
                layer=layer or "",
                collection=name or "",
                members=members,
                pattern=pattern,
            )
            return maya_success(
                "Updated collection {} in layer {}".format(result["collection"], result["layer"]),
                **result,
            )
        result = _create_collection(
            render_setup,
            layer=layer or "",
            name=name or "",
            members=members,
            pattern=pattern,
        )
        return maya_success(
            "Created collection {} in layer {}".format(result["collection"], result["layer"]),
            **result,
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid render collection request",
            str(exc),
            possible_solutions=[
                "Pass either members (explicit node names) or pattern, never both.",
                "Create the render layer first with create_render_layer.",
                "Use replace=true to change an existing collection instead of creating one.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.app.renderSetup could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create render collection")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_render_collection`."""
    return create_render_collection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
