"""Store pipeline metadata attributes on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_META_ATTRS = ["asset_name", "asset_variant", "asset_version", "pipeline_step"]


def tag_asset_metadata(
    node: str,
    asset_name: Optional[str] = None,
    asset_variant: Optional[str] = None,
    asset_version: Optional[str] = None,
    pipeline_step: Optional[str] = None,
) -> dict:
    """Tag a node with pipeline metadata string attributes.

    Args:
        node: Target node name.
        asset_name: Asset identifier (e.g. ``"hero_character"``).
        asset_variant: Variant / LOD tag (e.g. ``"HiRes"``, ``"proxy"``).
        asset_version: Version string (e.g. ``"v003"``).
        pipeline_step: Pipeline step (e.g. ``"modeling"``, ``"rigging"``, ``"shading"``).

    Returns:
        ActionResultModel dict with ``context.metadata`` dict of written values.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not node:
        return error_result("No node provided", "Provide 'node' parameter.").to_dict()

    values = {
        "asset_name": asset_name,
        "asset_variant": asset_variant,
        "asset_version": asset_version,
        "pipeline_step": pipeline_step,
    }
    non_empty = {k: v for k, v in values.items() if v}
    if not non_empty:
        return error_result(
            "No metadata provided",
            "Provide at least one of: {}.".format(", ".join(_META_ATTRS)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node):
            return error_result("Node not found", "No node named '{}'.".format(node)).to_dict()

        for attr, value in non_empty.items():
            if not cmds.attributeQuery(attr, node=node, exists=True):
                cmds.addAttr(node, longName=attr, dataType="string")
            cmds.setAttr("{}.{}".format(node, attr), str(value), type="string")

        return success_result(
            "Tagged '{}' with {} metadata attributes".format(node, len(non_empty)),
            prompt="Metadata tagged. Use get_asset_metadata to verify the values.",
            node=node,
            metadata=non_empty,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("tag_asset_metadata failed")
        return error_result("Failed to tag metadata", str(exc)).to_dict()


def main(**kwargs):
    return tag_asset_metadata(**kwargs)


if __name__ == "__main__":
    import json

    result = tag_asset_metadata("pSphere1", asset_name="hero", pipeline_step="modeling")
    print(json.dumps(result))
