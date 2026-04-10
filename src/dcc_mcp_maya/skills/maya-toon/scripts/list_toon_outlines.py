"""List all pfxToon nodes in the scene with their linked meshes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_toon_outlines() -> dict:
    """List all pfxToon outline nodes and their linked meshes.

    Returns:
        ActionResultModel dict with a list of toon outline info dicts.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        toon_nodes = cmds.ls(type="pfxToon") or []
        result = []
        for node in toon_nodes:
            info = {"node": node, "meshes": [], "line_width": None}  # type: dict
            try:
                info["line_width"] = cmds.getAttr("{}.lineWidth".format(node))
            except Exception:
                pass

            # Find connected meshes via displaySurface compound array
            try:
                connections = cmds.listConnections(
                    node, source=True, destination=False, type="mesh"
                ) or []
                info["meshes"] = list(set(connections))
            except Exception:
                pass

            result.append(info)

        return success_result(
            "Found {} pfxToon outline(s)".format(len(result)),
            prompt="Use set_outline_width to adjust width or add_toon_outline to add new outlines.",
            outlines=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_toon_outlines failed")
        return error_result("Failed to list toon outlines", str(exc)).to_dict()


def main(**kwargs):
    return list_toon_outlines(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_toon_outlines()))
