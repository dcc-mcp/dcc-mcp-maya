"""Query or create Maya scriptNode entries."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def get_script_node(
    node_name: str,
    action: str = "get",
    script: Optional[str] = None,
    script_type: int = 0,
) -> dict:
    """Get, create or delete a Maya scriptNode.

    Args:
        node_name: scriptNode name.
        action: ``"get"`` | ``"create"`` | ``"delete"``. Default ``"get"``.
        script: Script body (required when ``action == "create"``).
        script_type: 0=demand, 1=open/close, 2=ui create, 3=ui delete. Default 0.

    Returns:
        ToolResult dict with ``context.script_node`` info dict.
    """

    if not node_name:
        return skill_error("No scriptNode name provided", "Provide 'node_name' parameter.")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if action == "get":
            err = validate_node_exists(cmds, node_name)
            if err:
                return err
            body = cmds.getAttr("{}.before".format(node_name))
            stype = cmds.getAttr("{}.scriptType".format(node_name))
            return skill_success(
                "scriptNode retrieved",
                prompt="Inspect 'script_node' for the stored script body.",
                script_node={"name": node_name, "script": body, "script_type": stype},
                script=body,
                node_name=node_name,
            )

        elif action == "create":
            if not script:
                return skill_error("No script body provided", "Provide 'script' parameter.")
            node = cmds.scriptNode(
                scriptType=script_type,
                beforeScript=script,
                name=node_name,
                sourceType="python",
            )
            return skill_success(
                "scriptNode created: {}".format(node),
                prompt="scriptNode '{}' created. Use action='get' to verify.".format(node),
                script_node={"name": node, "script": script, "script_type": script_type},
            )

        elif action == "delete":
            if cmds.objExists(node_name):
                cmds.delete(node_name)
            return skill_success(
                "scriptNode deleted: {}".format(node_name),
                prompt="scriptNode '{}' removed from scene.".format(node_name),
                deleted=node_name,
            )

        else:
            return skill_error(
                "Unknown action '{}'".format(action),
                "Valid actions: get, create, delete.",
            )

    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="scriptNode operation failed")


@skill_entry
def main(**kwargs):
    return get_script_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
