"""Create a proxy (low-res stand-in) mesh from a high-res source object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def create_proxy(
    source: str,
    reduction: float = 90.0,
    proxy_name: Optional[str] = None,
    keep_original_visible: bool = False,
) -> dict:
    """Create a proxy mesh from a high-res object.

    Duplicates the source, reduces polygon count via ``polyReduce``, and tags
    the duplicate with custom ``isProxy``/``proxySource`` attributes.

    Args:
        source: High-res mesh transform name.
        reduction: Polygon reduction percentage 0–100. Default ``90.0``.
        proxy_name: Optional name for the proxy mesh.
        keep_original_visible: If ``False``, hide the original after creating proxy.

    Returns:
        ActionResultModel dict with ``context.proxy``, ``context.source``,
        and ``context.proxy_face_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source):
            return maya_error(
                "Source mesh '{}' not found".format(source),
                "Verify the mesh name in the Outliner.",
            )

        reduction = max(0.0, min(100.0, float(reduction)))
        percentage = (100.0 - reduction) / 100.0

        dup = cmds.duplicate(source, name=proxy_name if proxy_name else source + "_proxy")[0]

        shapes = cmds.listRelatives(dup, shapes=True, type="mesh") or []
        if shapes:
            cmds.polyReduce(dup, percentage=percentage, keepOriginalVertices=False, version=1)

        if not cmds.attributeQuery("isProxy", node=dup, exists=True):
            cmds.addAttr(dup, longName="isProxy", attributeType="bool", defaultValue=True)
        if not cmds.attributeQuery("proxySource", node=dup, exists=True):
            cmds.addAttr(dup, longName="proxySource", dataType="string")
        cmds.setAttr("{}.proxySource".format(dup), source, type="string")

        if not keep_original_visible:
            cmds.setAttr("{}.visibility".format(source), False)
            cmds.setAttr("{}.visibility".format(dup), True)

        proxy_poly = cmds.polyEvaluate(dup, face=True)

        return maya_success(
            "Proxy mesh '{}' created from '{}'".format(dup, source),
            prompt="Proxy ready. Use swap_proxy to toggle between proxy and high-res.",
            proxy=dup,
            source=source,
            reduction_percent=reduction,
            proxy_face_count=proxy_poly,
            original_visible=keep_original_visible,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create proxy mesh")

def main(**kwargs):
    return create_proxy(**kwargs)

if __name__ == "__main__":
    import json

    result = create_proxy("pSphere1")
    print(json.dumps(result))
