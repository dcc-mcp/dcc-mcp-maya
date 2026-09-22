"""Wire two comp nodes together."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import INPUT_PLUGS, CompositingContractError
from dcc_mcp_maya.compositing import connect_comp as _connect_comp


def connect_comp_nodes(
    source: Optional[str] = None,
    destination: Optional[str] = None,
    source_attr: str = "outColor",
) -> dict:
    """Connect a source output into the destination's first free input."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _connect_comp(cmds, source=source or "", destination=destination or "", source_attr=source_attr)
        return maya_success(
            "Connected {} -> {}".format(result["source"], result["destination"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid comp connection",
            str(exc),
            possible_solutions=[
                "Supported destination types: " + ", ".join(sorted(INPUT_PLUGS)),
                "A file node is a source, not a destination.",
                "source_attr defaults to outColor; pass another plug if needed.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to connect comp nodes")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_comp_nodes`."""
    return connect_comp_nodes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
