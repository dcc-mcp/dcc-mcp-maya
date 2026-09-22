"""Create an empty layeredTexture stack to composite layers into."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import CompositingContractError
from dcc_mcp_maya.compositing import create_layer_stack as _create_stack


def create_layer_stack(name: Optional[str] = None) -> dict:
    """Create an empty layer stack."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _create_stack(cmds, name=name)
        return maya_success(
            "Created layer stack {}".format(result["node"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid layer stack request",
            str(exc),
            possible_solutions=["Pass a name that no existing node uses."],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create layer stack")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_layer_stack`."""
    return create_layer_stack(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
