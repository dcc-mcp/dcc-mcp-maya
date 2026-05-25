"""Connect or disconnect Maya dynamic fields from dynamic objects."""

from __future__ import annotations

from typing import Any, List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success, validate_node_exists


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def connect_dynamic_field(targets: List[str], field: str, disconnect: bool = False) -> dict:
    """Connect or disconnect *field* from one or more dynamic targets."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        target_nodes = _as_list(targets)
        if not target_nodes:
            return maya_error("No dynamic targets provided", "Pass one or more target object names.")
        err = batch_validate_nodes(cmds, target_nodes)
        if err:
            return err
        err = validate_node_exists(cmds, field)
        if err:
            return err

        if disconnect:
            cmds.connectDynamic(target_nodes, fields=str(field), delete=True)
            message = "Disconnected field {} from {} target(s)".format(field, len(target_nodes))
        else:
            cmds.connectDynamic(target_nodes, fields=str(field))
            message = "Connected field {} to {} target(s)".format(field, len(target_nodes))

        return maya_success(
            message,
            field=str(field),
            targets=target_nodes,
            disconnected=bool(disconnect),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to connect dynamic field")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_dynamic_field`."""
    return connect_dynamic_field(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
