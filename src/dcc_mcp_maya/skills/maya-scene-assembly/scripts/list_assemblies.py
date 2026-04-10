"""List all Assembly Reference nodes in the scene."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """List all assemblyReference nodes in the current scene.

    Args:
        params: Empty dict (no parameters needed).

    Returns:
        ActionResultModel with list of assembly node info dicts.
    """
    try:
        nodes = cmds.ls(type="assemblyReference") or []
        result: List[Dict[str, object]] = []
        for node in nodes:
            info: Dict[str, object] = {"name": node}
            try:
                info["definition"] = cmds.getAttr("{}.definition".format(node)) or ""
            except Exception:
                info["definition"] = ""
            try:
                active_rep = cmds.assembly(node, query=True, activeRepresentation=True)
                info["active_representation"] = active_rep or ""
            except Exception:
                info["active_representation"] = ""
            result.append(info)
        return success_result(
            "Found {} assembly reference node(s)".format(len(result)),
            prompt="Use activate_assembly_representation to change the active LOD.",
            assemblies=result,
            count=len(result),
        )
    except Exception as exc:
        return error_result("Failed to list assembly references", str(exc))
