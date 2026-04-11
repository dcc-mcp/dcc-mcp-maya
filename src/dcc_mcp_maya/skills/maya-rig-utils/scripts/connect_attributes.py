"""Connect one or more source attributes to destination attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def connect_attributes(
    connections: List[List[str]],
    force: bool = False,
) -> dict:
    """Connect source attributes to destination attributes.

    Args:
        connections: List of ``[source_attr, destination_attr]`` pairs.
            Each entry is a two-element list where the first element is the
            fully qualified source attribute (e.g. ``"node.tx"``) and the
            second is the destination attribute (e.g. ``"other.tx"``).
        force: If True, break existing incoming connections before connecting.
            Default: False.

    Returns:
        ActionResultModel dict with ``context.connected_count`` and
        ``context.failed_connections``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not connections:
            return skill_error(
                "No connections specified",
                "connections list must contain at least one [source, dest] pair",
            )

        connected = []
        failed = []

        for pair in connections:
            if len(pair) != 2:
                failed.append({"pair": pair, "error": "must be a 2-element list"})
                continue

            src, dst = pair[0], pair[1]
            try:
                if force and cmds.connectionInfo(dst, isDestination=True):
                    cmds.disconnectAttr(cmds.connectionInfo(dst, getExactDestination=True), dst)
                cmds.connectAttr(src, dst, force=force)
                connected.append([src, dst])
            except Exception as exc:
                failed.append({"pair": [src, dst], "error": str(exc)})

        if not connected and failed:
            return skill_error(
                "All {} connection(s) failed".format(len(failed)),
                "; ".join(f["error"] for f in failed),
            )

        return skill_success(
            "Connected {}/{} attribute pair(s)".format(len(connected), len(connections)),
            prompt="Use lock_hide_attributes if driven attrs should not be keyable.",
            connected_count=len(connected),
            connected=connected,
            failed_connections=failed,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to connect attributes")


@skill_entry
def main(**kwargs):
    return connect_attributes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
