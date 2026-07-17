"""Connect or disconnect two ports in a Bifrost graph."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import connect_ports, ensure_bifrost_plugins


def connect_bifrost_ports(
    graph: str,
    source_port: str,
    destination_port: str,
    disconnect: bool = False,
    copy_metadata: bool = False,
) -> dict:
    """Connect or disconnect two absolute-from-root VNN port paths."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        connection = connect_ports(
            cmds,
            graph,
            source_port,
            destination_port,
            disconnect=bool(disconnect),
            copy_metadata=bool(copy_metadata),
        )
        action = "Disconnected" if disconnect else "Connected"
        return maya_success(
            "{} Bifrost ports".format(action), runtime=runtime, copy_metadata=bool(copy_metadata), **connection
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to update Bifrost port connection")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_bifrost_ports`."""
    return connect_bifrost_ports(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
