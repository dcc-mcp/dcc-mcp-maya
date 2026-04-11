"""List all Bifrost graph nodes in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success



def list_bifrost_graphs() -> dict:
    """List all ``bifrostGraph`` nodes present in the scene.

    Returns:
        ActionResultModel dict with ``context.graphs`` (list of node names)
        and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        graphs = cmds.ls(type="bifrostGraph") or []
        return maya_success(
            "Found {} Bifrost graph(s)".format(len(graphs)),
            prompt="Use add_bifrost_node to add compounds or connect_bifrost_ports to wire ports.",
            graphs=graphs,
            count=len(graphs),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list Bifrost graphs")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_bifrost_graphs`."""
    return list_bifrost_graphs(**kwargs)


if __name__ == "__main__":
    import json

    result = list_bifrost_graphs()
    print(json.dumps(result))
