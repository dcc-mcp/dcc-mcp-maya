"""Create a dynamic input or output port on a Bifrost node."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import create_port, ensure_bifrost_plugins


def create_bifrost_port(
    graph: str,
    node: str,
    port: str,
    data_type: str,
    direction: str = "input",
) -> dict:
    """Create a dynamic Bifrost port, for example an Object array input."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        created = create_port(cmds, graph, node, port, data_type, direction=direction)
        return maya_success("Created Bifrost {} port: {}.{}".format(direction, node, port), runtime=runtime, **created)
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create Bifrost port")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_bifrost_port`."""
    return create_bifrost_port(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
