"""Create a generic Maya dependency graph or DAG node."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, summarize_node, validate_node_exists


def create_node(
    node_type: str,
    name: Optional[str] = None,
    parent: Optional[str] = None,
    skip_select: bool = True,
    shared: bool = False,
) -> dict:
    """Create a Maya node using ``cmds.createNode``."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not node_type or not str(node_type).strip():
            return maya_error("Invalid node_type", "node_type must be a non-empty Maya node type.")
        if parent:
            err = validate_node_exists(cmds, parent)
            if err:
                return err
        kwargs = {
            "skipSelect": bool(skip_select),
            "shared": bool(shared),
        }
        if name:
            kwargs["name"] = str(name)
        if parent:
            kwargs["parent"] = str(parent)
        node = str(cmds.createNode(str(node_type), **kwargs))
        return maya_success(
            "Created {} node: {}".format(node_type, node),
            node_name=node,
            node_type=str(node_type),
            node=summarize_node(cmds, node),
            parent=parent,
            shared=bool(shared),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create Maya node")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_node`."""
    return create_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
