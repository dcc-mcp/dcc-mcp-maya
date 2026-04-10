"""List all Maya oceanShader nodes in the current scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_oceans() -> dict:
    """List all oceanShader nodes in the scene.

    Returns:
        ActionResultModel dict with ``context.oceans`` list and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ocean_nodes = cmds.ls(type="oceanShader") or []
        oceans = []
        for node in ocean_nodes:
            info = {"name": node}
            for attr in ("waveHeight", "waveTurbulence", "waveSpeed"):
                try:
                    info[attr] = cmds.getAttr("{}.{}".format(node, attr))
                except Exception:
                    pass
            oceans.append(info)

        return success_result(
            "Found {} ocean shader(s)".format(len(oceans)),
            prompt=(
                "Use set_ocean_attribute to modify wave properties, "
                "or delete_ocean to remove an ocean."
            ),
            oceans=oceans,
            count=len(oceans),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_oceans failed")
        return error_result("Failed to list oceans", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_oceans(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_oceans()))
