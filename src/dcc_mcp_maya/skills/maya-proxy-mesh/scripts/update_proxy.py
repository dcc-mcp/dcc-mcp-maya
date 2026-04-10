"""Regenerate an existing proxy mesh from its updated high-res source."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Delete and re-create a proxy from the current state of its source mesh.

    Looks up the proxy by *lod_level=0* tag and the source by *lod_level=1*
    tag.  The proxy is deleted, then :func:`create_proxy.run` logic is
    re-applied with the same parameters.

    Args:
        params: Dictionary containing:
            - proxy (str): Name of the existing proxy transform.  Required.
            - method (str): 'bbox' or 'reduce'.  Default 'bbox'.
            - reduce_percent (float): Reduction percentage.  Default 10.0.
            - hide_source (bool): Hide source after regeneration.  Default False.

    Returns:
        ActionResultModel with updated proxy name and poly count.
    """
    proxy = str(params.get("proxy", "")).strip()
    method = str(params.get("method", "bbox")).lower()
    reduce_percent = float(params.get("reduce_percent", 10.0))
    hide_source = bool(params.get("hide_source", False))

    if not proxy:
        return error_result("Invalid parameters", "'proxy' is required.")
    if method not in ("bbox", "reduce"):
        return error_result(
            "Invalid method",
            "method must be 'bbox' or 'reduce', got '{}'.".format(method),
        )

    try:
        if not cmds.objExists(proxy):
            return error_result("Proxy not found", "No node named '{}' exists.".format(proxy))

        # Verify it carries lod_level=0
        if not cmds.attributeQuery("lod_level", node=proxy, exists=True):
            return error_result(
                "Not a proxy",
                "'{}' has no lod_level attribute; it may not be a managed proxy.".format(proxy),
            )
        if cmds.getAttr("{}.lod_level".format(proxy)) != 0:
            return error_result(
                "Not a proxy",
                "'{}' has lod_level != 0; pass the proxy (not the source) node.".format(proxy),
            )

        # Find source: look for sibling with lod_level=1
        parent = cmds.listRelatives(proxy, parent=True) or []
        siblings = cmds.listRelatives(parent[0], children=True, type="transform") if parent else []
        source = None
        for sib in siblings:
            if sib == proxy:
                continue
            if cmds.attributeQuery("lod_level", node=sib, exists=True):
                if cmds.getAttr("{}.lod_level".format(sib)) == 1:
                    source = sib
                    break

        if source is None:
            return error_result(
                "Source not found",
                "Could not locate a sibling with lod_level=1 for proxy '{}'.".format(proxy),
            )

        # Delete old proxy
        cmds.delete(proxy)

        # Re-create with same name
        proxy_name = proxy
        poly_count = 0
        proxy_transform = None

        if method == "bbox":
            bb = cmds.exactWorldBoundingBox(source)
            cx = (bb[0] + bb[3]) / 2.0
            cy = (bb[1] + bb[4]) / 2.0
            cz = (bb[2] + bb[5]) / 2.0
            sx = bb[3] - bb[0]
            sy = bb[4] - bb[1]
            sz = bb[5] - bb[2]
            result = cmds.polyCube(
                name=proxy_name,
                width=max(sx, 0.001),
                height=max(sy, 0.001),
                depth=max(sz, 0.001),
            )
            proxy_transform = result[0]
            cmds.move(cx, cy, cz, proxy_transform, absolute=True)
            poly_count = 6
        else:
            dup = cmds.duplicate(source, name=proxy_name)[0]
            shapes = cmds.listRelatives(dup, shapes=True, type="mesh") or []
            if not shapes:
                cmds.delete(dup)
                return error_result(
                    "No mesh shape found",
                    "Source '{}' has no mesh shape to reduce.".format(source),
                )
            cmds.polyReduce(dup, percentage=reduce_percent, keepQuadsWeight=1)
            proxy_transform = dup
            try:
                poly_count = cmds.polyEvaluate(dup, face=True)
            except Exception:
                poly_count = 0

        # Re-tag
        for node, level in [(source, 1), (proxy_transform, 0)]:
            if not cmds.attributeQuery("lod_level", node=node, exists=True):
                cmds.addAttr(node, longName="lod_level", attributeType="short")
            cmds.setAttr("{}.lod_level".format(node), level)

        if hide_source:
            cmds.hide(source)

        return success_result(
            "Updated proxy '{}' from source '{}' using method '{}'".format(
                proxy_transform, source, method
            ),
            prompt="Proxy updated. Use swap_proxy to toggle visibility.",
            proxy=proxy_transform,
            source=source,
            method=method,
            poly_count=poly_count,
        )
    except Exception as exc:
        logger.exception("update_proxy failed")
        return error_result("Failed to update proxy '{}'".format(proxy), str(exc))
