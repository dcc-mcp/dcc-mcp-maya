"""List all display layers in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def list_display_layers() -> dict:
    """List all display layers in the scene.

    Returns:
        ActionResultModel dict with ``context.layers`` — a list of dicts
        with ``name``, ``visible``, ``display_type``, and ``member_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        layer_nodes = cmds.ls(type="displayLayer") or []
        layers = []
        for layer in layer_nodes:
            members = cmds.editDisplayLayerMembers(layer, query=True) or []
            layers.append(
                {
                    "name": layer,
                    "visible": bool(cmds.getAttr("{}.visibility".format(layer))),
                    "display_type": int(cmds.getAttr("{}.displayType".format(layer))),
                    "member_count": len(members),
                }
            )

        return success_result(
            "Found {} display layer(s)".format(len(layers)),
            layers=layers,
            count=len(layers),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_display_layers failed")
        return error_result("Failed to list display layers", str(exc)).to_dict()



def main(**kwargs):
    return list_display_layers(**kwargs)


if __name__ == "__main__":
    import json
    result = list_display_layers()
    print(json.dumps(result))
