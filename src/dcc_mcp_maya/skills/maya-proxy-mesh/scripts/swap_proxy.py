"""Toggle visibility between a proxy mesh and its high-res source."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional


def swap_proxy(proxy: str, show_proxy: Optional[bool] = None) -> dict:
    """Swap visibility between proxy and high-res mesh.

    Args:
        proxy: Proxy mesh transform name.
        show_proxy: ``True`` = show proxy / hide source, ``False`` = show source / hide proxy.
            If ``None``, toggles the current state.

    Returns:
        ActionResultModel dict with ``context.proxy_visible`` and ``context.source_visible``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(proxy):
            return maya_error(
                "Proxy mesh '{}' not found".format(proxy),
                "Use list_proxies to find available proxy meshes.",
            )

        source = ""
        if cmds.attributeQuery("proxySource", node=proxy, exists=True):
            source = cmds.getAttr("{}.proxySource".format(proxy)) or ""

        current_proxy_vis = cmds.getAttr("{}.visibility".format(proxy))

        if show_proxy is None:
            show_proxy = not current_proxy_vis

        cmds.setAttr("{}.visibility".format(proxy), bool(show_proxy))

        source_vis = None
        if source and cmds.objExists(source):
            cmds.setAttr("{}.visibility".format(source), not bool(show_proxy))
            source_vis = not bool(show_proxy)

        return maya_success(
            "Proxy='{}' visibility={}, Source='{}' visibility={}".format(proxy, show_proxy, source, source_vis),
            prompt="Visibility swapped. Use swap_proxy again to toggle back.",
            proxy=proxy,
            proxy_visible=bool(show_proxy),
            source=source,
            source_visible=source_vis,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to swap proxy visibility")


def main(**kwargs):
    return swap_proxy(**kwargs)


if __name__ == "__main__":
    import json

    result = swap_proxy("pSphere1_proxy")
    print(json.dumps(result))
