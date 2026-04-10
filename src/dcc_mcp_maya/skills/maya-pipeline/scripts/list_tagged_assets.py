"""List all nodes in the scene that have pipeline asset tags."""
from __future__ import annotations

from typing import Dict, List, Optional

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

_PIPELINE_ATTRS: List[str] = [
    "pipeline_asset_name",
    "pipeline_asset_type",
    "pipeline_shot",
    "pipeline_step",
    "pipeline_version",
    "pipeline_note",
]


def run(params: Dict[str, object]) -> object:
    """List all scene nodes that have been tagged with pipeline metadata.

    Args:
        params: Dictionary containing:
            - asset_type_filter (str): Optional asset_type value to filter by.
            - step_filter (str): Optional pipeline_step value to filter by.

    Returns:
        ActionResultModel with list of tagged node info dicts.
    """
    asset_type_filter: Optional[str] = params.get("asset_type_filter", None)  # type: ignore[assignment]
    step_filter: Optional[str] = params.get("step_filter", None)  # type: ignore[assignment]

    try:
        # Find nodes that have the sentinel attribute
        tagged_nodes: List[str] = (
            cmds.ls("*.pipeline_asset_name", objectsOnly=True, long=False) or []
        )

        results: List[Dict[str, object]] = []
        for node in tagged_nodes:
            tags: Dict[str, str] = {}
            for attr in _PIPELINE_ATTRS:
                if cmds.attributeQuery(attr, node=node, exists=True):
                    val = cmds.getAttr("{}.{}".format(node, attr))
                    tags[attr] = val if val else ""

            # Apply filters
            if asset_type_filter and tags.get("pipeline_asset_type") != asset_type_filter:
                continue
            if step_filter and tags.get("pipeline_step") != step_filter:
                continue

            results.append({"node": node, "tags": tags})

        return success_result(
            "Found {} tagged asset(s)".format(len(results)),
            prompt="Use tag_asset to add metadata to untagged nodes.",
            assets=results,
            count=len(results),
        )
    except Exception as exc:
        return error_result("Failed to list tagged assets", str(exc))
