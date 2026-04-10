"""Create a low-resolution proxy mesh from an existing high-res mesh."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Generate a bounding-box or reduced proxy for a high-resolution mesh.

    The proxy is created as a separate mesh parented at the same level as
    the source.  An 'lod_level' attribute is added to both to allow easy
    identification.

    Args:
        params: Dictionary containing:
            - source (str): Name of the high-res mesh transform.  Required.
            - proxy_name (str): Name for the proxy transform.
                                Default '<source>_proxy'.
            - method (str): 'bbox' (bounding box cube) or 'reduce'
                            (poly reduce at given percentage).  Default 'bbox'.
            - reduce_percent (float): Target percentage for poly reduce.
                                      Only used when method='reduce'.  Default 10.0.
            - hide_source (bool): Hide the source mesh after proxy creation.
                                  Default False.

    Returns:
        ActionResultModel with proxy mesh name and polygon count.
    """
    source = str(params.get("source", "")).strip()
    proxy_name = str(params.get("proxy_name", "")).strip()
    method = str(params.get("method", "bbox")).lower()
    reduce_percent = float(params.get("reduce_percent", 10.0))
    hide_source = bool(params.get("hide_source", False))

    if not source:
        return error_result("Invalid parameters", "'source' is required.")
    if not proxy_name:
        proxy_name = "{}_proxy".format(source)
    if method not in ("bbox", "reduce"):
        return error_result(
            "Invalid method",
            "method must be 'bbox' or 'reduce', got '{}'.".format(method),
        )

    try:
        if not cmds.objExists(source):
            return error_result(
                "Source not found",
                "No node named '{}' exists.".format(source),
            )

        proxy_transform = None
        poly_count = 0

        if method == "bbox":
            # Get world-space bounding box and create a cube proxy
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
            poly_count = 6  # bbox cube has 6 faces

        else:  # reduce
            # Duplicate source and apply polyReduce
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

        # Tag both meshes with lod_level attribute
        for node, level in [(source, 1), (proxy_transform, 0)]:
            if not cmds.attributeQuery("lod_level", node=node, exists=True):
                cmds.addAttr(node, longName="lod_level", attributeType="short")
            cmds.setAttr("{}.lod_level".format(node), level)

        if hide_source:
            cmds.hide(source)

        return success_result(
            "Created proxy '{}' from '{}' using method '{}'".format(proxy_name, source, method),
            prompt="Use swap_proxy to toggle between proxy and high-res mesh.",
            proxy=proxy_transform,
            source=source,
            method=method,
            poly_count=poly_count,
        )
    except Exception as exc:
        logger.exception("create_proxy failed")
        return error_result("Failed to create proxy for '{}'".format(source), str(exc))
