"""Return the full DAG path of a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        # ls -long returns full DAG paths
        full_paths = cmds.ls(object_name, long=True)
        if not full_paths:
            return skill_error(
                "Could not resolve DAG path for: {}".format(object_name),
                "cmds.ls returned empty list",
            )

        dag_path = full_paths[0]
        node_type = cmds.objectType(object_name)
        short_name = dag_path.split("|")[-1]

        return skill_success(
            "DAG path for '{}': {}".format(object_name, dag_path),
            dag_path=dag_path,
            short_name=short_name,
            node_type=node_type,
            object_name=object_name,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get DAG path for {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_dag_path`."""
    return get_dag_path(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
