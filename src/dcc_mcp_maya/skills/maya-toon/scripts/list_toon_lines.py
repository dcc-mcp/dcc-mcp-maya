"""List all Maya pfxToon outline nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_toon_lines() -> dict:
    """List all pfxToon nodes in the scene.

    Returns:
        ActionResultModel dict with ``context.toon_lines`` and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        toon_nodes = cmds.ls(type="pfxToon") or []
        toon_lines = []
        for node in toon_nodes:
            info = {"name": node}
            for attr in ("profileLineWidth", "creaseLineWidth"):
                try:
                    info[attr] = cmds.getAttr("{}.{}".format(node, attr))
                except Exception:
                    pass
            toon_lines.append(info)

        return success_result(
            "Found {} pfxToon node(s)".format(len(toon_lines)),
            prompt=(
                "Use set_toon_attribute to modify line properties, "
                "or delete_toon_line to remove an outline."
            ),
            toon_lines=toon_lines,
            count=len(toon_lines),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_toon_lines failed")
        return error_result("Failed to list toon lines", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_toon_lines(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_toon_lines()))
