"""List all Particle Instancer nodes in the scene."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """List all instancer nodes in the current scene.

    Args:
        params: Empty dict (no parameters needed).

    Returns:
        ActionResultModel with a list of instancer info dicts.
    """
    try:
        nodes = cmds.ls(type="instancer") or []
        result: List[Dict[str, object]] = []
        for node in nodes:
            info: Dict[str, object] = {"name": node}
            try:
                objects = cmds.particleInstancer(node, query=True, object=True) or []
                info["instance_objects"] = list(objects)
            except Exception:
                info["instance_objects"] = []
            result.append(info)
        return success_result(
            "Found {} instancer node(s)".format(len(result)),
            prompt="Use add_instancer_object to attach additional instance objects.",
            instancers=result,
            count=len(result),
        )
    except Exception as exc:
        return error_result("Failed to list instancers", str(exc))
