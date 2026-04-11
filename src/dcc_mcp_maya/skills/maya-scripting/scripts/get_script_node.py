"""Query or create Maya scriptNode entries."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result("No scriptNode name provided", "Provide 'name' parameter.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if action == "get":
            if not cmds.objExists(name):
                return error_result("scriptNode not found", "No node named '{}'.".format(name)).to_dict()
            body = cmds.getAttr("{}.before".format(name))
            stype = cmds.getAttr("{}.scriptType".format(name))
            return success_result(
                "scriptNode retrieved",
                prompt="Inspect 'script_node' for the stored script body.",
                script_node={"name": name, "script": body, "script_type": stype},
            ).to_dict()

        elif action == "create":
            if not script:
                return error_result("No script body provided", "Provide 'script' parameter.").to_dict()
            node = cmds.scriptNode(
                scriptType=script_type,
                beforeScript=script,
                name=name,
                sourceType="python",
            )
            return success_result(
                "scriptNode created: {}".format(node),
                prompt="scriptNode '{}' created. Use action='get' to verify.".format(node),
                script_node={"name": node, "script": script, "script_type": script_type},
            ).to_dict()

        elif action == "delete":
            if cmds.objExists(name):
                cmds.delete(name)
            return success_result(
                "scriptNode deleted: {}".format(name),
                prompt="scriptNode '{}' removed from scene.".format(name),
                deleted=name,
            ).to_dict()

        else:
            return error_result(
                "Unknown action '{}'".format(action),
                "Valid actions: get, create, delete.",
            ).to_dict()

    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_script_node failed")
        return error_result("scriptNode operation failed", str(exc)).to_dict()


def main(**kwargs):
    return get_script_node(**kwargs)


if __name__ == "__main__":
    import json

    result = get_script_node("myScript", action="get")
    print(json.dumps(result))
