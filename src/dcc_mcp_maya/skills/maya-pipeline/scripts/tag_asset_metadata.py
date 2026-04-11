"""Store pipeline metadata attributes on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

_META_ATTRS = ["asset_name", "asset_variant", "asset_version", "pipeline_step"]


# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success  # noqa: E402


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

    if not node:
        return skill_error("No node provided", "Provide 'node' parameter.")

    values = {
        "asset_name": asset_name,
        "asset_variant": asset_variant,
        "asset_version": asset_version,
        "pipeline_step": pipeline_step,
    }
    non_empty = {k: v for k, v in values.items() if v}
    if not non_empty:
        return skill_error(
            "No metadata provided",
            "Provide at least one of: {}.".format(", ".join(_META_ATTRS)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node):
            return skill_error("Node not found", "No node named '{}'.".format(node))

        for attr, value in non_empty.items():
            if not cmds.attributeQuery(attr, node=node, exists=True):
                cmds.addAttr(node, longName=attr, dataType="string")
            cmds.setAttr("{}.{}".format(node, attr), str(value), type="string")

        return skill_success(
            "Tagged '{}' with {} metadata attributes".format(node, len(non_empty)),
            prompt="Metadata tagged. Use get_asset_metadata to verify the values.",
            node=node,
            metadata=non_empty,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to tag metadata")


@skill_entry
def main(**kwargs):
    return tag_asset_metadata(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
