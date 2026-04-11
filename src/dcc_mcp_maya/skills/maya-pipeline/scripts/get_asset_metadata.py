"""Retrieve pipeline metadata attributes from a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

_META_ATTRS = ["asset_name", "asset_variant", "asset_version", "pipeline_step"]


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def get_asset_metadata(node: str) -> dict:
    """Read pipeline metadata string attributes from a node.

    Args:
        node: Target node name.

    Returns:
        ActionResultModel dict with ``context.metadata`` dict.
        Missing attributes are returned as empty strings.
    """

    if not node:
        return maya_error("No node provided", "Provide 'node' parameter.")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node):
            return maya_error("Node not found", "No node named '{}'.".format(node))

        metadata = {}
        for attr in _META_ATTRS:
            if cmds.attributeQuery(attr, node=node, exists=True):
                metadata[attr] = cmds.getAttr("{}.{}".format(node, attr)) or ""
            else:
                metadata[attr] = ""

        tagged = [k for k, v in metadata.items() if v]
        return maya_success(
            "Retrieved metadata from '{}' ({} tagged)".format(node, len(tagged)),
            prompt=("Metadata retrieved. Use tag_asset_metadata to update any empty fields before publishing."),
            node=node,
            metadata=metadata,
            tagged_count=len(tagged),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get metadata")


def main(**kwargs):
    return get_asset_metadata(**kwargs)


if __name__ == "__main__":
    import json

    result = get_asset_metadata("pSphere1")
    print(json.dumps(result))
