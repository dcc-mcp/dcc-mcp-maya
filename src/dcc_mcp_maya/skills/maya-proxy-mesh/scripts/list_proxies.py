"""List all proxy meshes tracked by the isProxy custom attribute."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_proxies() -> dict:
    """List proxy mesh pairs (proxy + source).

    Finds all transform nodes with ``isProxy = True`` custom attribute.

    Returns:
        ActionResultModel dict with ``context.proxies`` list and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        all_transforms = cmds.ls(type="transform") or []
        proxies = []
        for node in all_transforms:
            if not cmds.attributeQuery("isProxy", node=node, exists=True):
                continue
            if not cmds.getAttr("{}.isProxy".format(node)):
                continue

            source = ""
            if cmds.attributeQuery("proxySource", node=node, exists=True):
                source = cmds.getAttr("{}.proxySource".format(node)) or ""

            proxy_vis = cmds.getAttr("{}.visibility".format(node))
            source_vis = None
            if source and cmds.objExists(source):
                source_vis = cmds.getAttr("{}.visibility".format(source))

            face_count = None
            try:
                face_count = cmds.polyEvaluate(node, face=True)
            except Exception:
                pass

            proxies.append(
                {
                    "proxy": node,
                    "source": source,
                    "proxy_visible": proxy_vis,
                    "source_visible": source_vis,
                    "face_count": face_count,
                }
            )

        return success_result(
            "Found {} proxy mesh pair(s)".format(len(proxies)),
            prompt="Use swap_proxy to toggle visibility or set_proxy_attribute to adjust render settings.",
            proxies=proxies,
            count=len(proxies),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_proxies failed")
        return error_result("Failed to list proxy meshes", str(exc)).to_dict()


def main(**kwargs):
    return list_proxies(**kwargs)


if __name__ == "__main__":
    import json

    result = list_proxies()
    print(json.dumps(result))
