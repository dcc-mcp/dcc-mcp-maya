"""Delete generic Maya nodes."""

from __future__ import annotations

from typing import Any, List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def delete_node(nodes: List[str]) -> dict:
    """Delete one or more Maya DG/DAG nodes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = _as_list(nodes)
        if not targets:
            return maya_error("No nodes provided", "Pass one or more Maya node names.")
        err = batch_validate_nodes(cmds, targets)
        if err:
            return err
        cmds.delete(targets)
        return maya_success(
            "Deleted {} node(s)".format(len(targets)),
            deleted_nodes=targets,
            count=len(targets),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to delete Maya node")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_node`."""
    return delete_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
