"""Set an unconnected Bifrost node port's default value."""

from __future__ import annotations

from typing import Any

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import ensure_bifrost_plugins, set_port_default


def set_bifrost_property(graph: str, node: str, port: str, value: Any) -> dict:
    """Set a scalar, vector, or array default on a Bifrost input port."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        updated = set_port_default(cmds, graph, node, port, value)
        return maya_success("Set Bifrost port default: {}.{}".format(node, port), runtime=runtime, **updated)
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to set Bifrost property")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_bifrost_property`."""
    return set_bifrost_property(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
