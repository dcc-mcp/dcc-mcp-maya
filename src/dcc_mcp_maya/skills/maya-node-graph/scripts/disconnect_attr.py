"""Disconnect two connected Maya node attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_success


def disconnect_attr(
    source_attr: str,
    dest_attr: str,
) -> dict:
    """Disconnect two connected Maya node attributes.

    Args:
        source_attr: Full attribute path of the driver, e.g.
            ``"pSphere1.translateX"``.
        dest_attr: Full attribute path of the driven attribute.

    Returns:
        ActionResultModel dict with ``context.source_attr`` and
        ``context.dest_attr``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, [source_attr, dest_attr])
        if err:
            return err

        # Check if actually connected before attempting disconnect
        if not cmds.isConnected(source_attr, dest_attr):
            return maya_error(
                "Attributes not connected: {} -> {}".format(source_attr, dest_attr),
                "No connection exists between these attributes",
            )

        cmds.disconnectAttr(source_attr, dest_attr)

        return maya_success(
            "Disconnected {} -x-> {}".format(source_attr, dest_attr),
            source_attr=source_attr,
            dest_attr=dest_attr,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error(
            "Failed to disconnect {} -> {}".format(source_attr, dest_attr),
            str(exc),
        )


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`disconnect_attr`."""
    return disconnect_attr(**kwargs)


if __name__ == "__main__":
    import json

    result = disconnect_attr()
    print(json.dumps(result))
