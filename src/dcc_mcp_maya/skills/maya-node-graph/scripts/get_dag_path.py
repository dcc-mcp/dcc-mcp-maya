"""Return the full DAG path of a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def get_dag_path(
    object_name: str,
) -> dict:
    """Return the full DAG path of a Maya node.

    Resolves the shortest unique path for the given node name, then returns
    its full absolute DAG path (e.g. ``"|group1|pSphere1"``).

    Args:
        object_name: Short or partial name of the node.

    Returns:
        ActionResultModel dict with ``context.dag_path`` (full path),
        ``context.short_name``, and ``context.node_type``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        # ls -long returns full DAG paths
        full_paths = cmds.ls(object_name, long=True)
        if not full_paths:
            return maya_error(
                "Could not resolve DAG path for: {}".format(object_name),
                "cmds.ls returned empty list",
            )

        dag_path = full_paths[0]
        node_type = cmds.objectType(object_name)
        short_name = dag_path.split("|")[-1]

        return maya_success(
            "DAG path for '{}': {}".format(object_name, dag_path),
            dag_path=dag_path,
            short_name=short_name,
            node_type=node_type,
            object_name=object_name,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get DAG path for {}".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_dag_path`."""
    return get_dag_path(**kwargs)


if __name__ == "__main__":
    import json

    result = get_dag_path()
    print(json.dumps(result))
