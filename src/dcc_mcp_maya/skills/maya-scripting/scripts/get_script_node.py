"""Query or create Maya scriptNode entries."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional


def get_script_node(
    name: str,
    action: str = "get",
    script: Optional[str] = None,
    script_type: int = 0,
) -> dict:
    """Get, create or delete a Maya scriptNode.

    Args:
        name: scriptNode name.
        action: ``"get"`` | ``"create"`` | ``"delete"``. Default ``"get"``.
        script: Script body (required when ``action == "create"``).
        script_type: 0=demand, 1=open/close, 2=ui create, 3=ui delete. Default 0.

    Returns:
        ActionResultModel dict with ``context.script_node`` info dict.
    """

    if not name:
        return maya_error("No scriptNode name provided", "Provide 'name' parameter.")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if action == "get":
            if not cmds.objExists(name):
                return maya_error("scriptNode not found", "No node named '{}'.".format(name))
            body = cmds.getAttr("{}.before".format(name))
            stype = cmds.getAttr("{}.scriptType".format(name))
            return maya_success(
                "scriptNode retrieved",
                prompt="Inspect 'script_node' for the stored script body.",
                script_node={"name": name, "script": body, "script_type": stype},
            )

        elif action == "create":
            if not script:
                return maya_error("No script body provided", "Provide 'script' parameter.")
            node = cmds.scriptNode(
                scriptType=script_type,
                beforeScript=script,
                name=name,
                sourceType="python",
            )
            return maya_success(
                "scriptNode created: {}".format(node),
                prompt="scriptNode '{}' created. Use action='get' to verify.".format(node),
                script_node={"name": node, "script": script, "script_type": script_type},
            )

        elif action == "delete":
            if cmds.objExists(name):
                cmds.delete(name)
            return maya_success(
                "scriptNode deleted: {}".format(name),
                prompt="scriptNode '{}' removed from scene.".format(name),
                deleted=name,
            )

        else:
            return maya_error(
                "Unknown action '{}'".format(action),
                "Valid actions: get, create, delete.",
            )

    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "scriptNode operation failed")


def main(**kwargs):
    return get_script_node(**kwargs)


if __name__ == "__main__":
    import json

    result = get_script_node("myScript", action="get")
    print(json.dumps(result))
