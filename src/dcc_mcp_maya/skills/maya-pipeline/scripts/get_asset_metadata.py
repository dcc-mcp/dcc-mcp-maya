"""Retrieve pipeline metadata attributes from a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

_META_ATTRS = ["asset_name", "asset_variant", "asset_version", "pipeline_step"]


def get_asset_metadata(node: str) -> dict:
    """Read pipeline metadata string attributes from a node.

    Args:
        node: Target node name.

    Returns:
        ActionResultModel dict with ``context.metadata`` dict.
        Missing attributes are returned as empty strings.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not node:
        return error_result("No node provided", "Provide 'node' parameter.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node):
            return error_result("Node not found", "No node named '{}'.".format(node)).to_dict()

        metadata = {}
        for attr in _META_ATTRS:
            if cmds.attributeQuery(attr, node=node, exists=True):
                metadata[attr] = cmds.getAttr("{}.{}".format(node, attr)) or ""
            else:
                metadata[attr] = ""

        tagged = [k for k, v in metadata.items() if v]
        return success_result(
            "Retrieved metadata from '{}' ({} tagged)".format(node, len(tagged)),
            prompt=("Metadata retrieved. Use tag_asset_metadata to update any empty fields before publishing."),
            node=node,
            metadata=metadata,
            tagged_count=len(tagged),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_asset_metadata failed")
        return error_result("Failed to get metadata", str(exc)).to_dict()


def main(**kwargs):
    return get_asset_metadata(**kwargs)


if __name__ == "__main__":
    import json

    result = get_asset_metadata("pSphere1")
    print(json.dumps(result))
