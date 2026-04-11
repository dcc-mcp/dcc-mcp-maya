"""Remove orphaned nodes and unknown plug-ins from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules


def clean_scene(
    remove_unknown_nodes: bool = True,
    remove_unknown_plugins: bool = True,
    remove_empty_display_layers: bool = True,
    remove_empty_render_layers: bool = False,
    dry_run: bool = False,
) -> dict:
    """Clean up the Maya scene by removing common orphaned node types.

    Args:
        remove_unknown_nodes: Delete unknown-type nodes. Default True.
        remove_unknown_plugins: Flush unresolved plug-in references. Default True.
        remove_empty_display_layers: Delete display layers with no members. Default True.
        remove_empty_render_layers: Delete non-default render layers with no members.
            Default False.
        dry_run: If True, only report what would be removed. Default False.

    Returns:
        ActionResultModel dict with ``context.removed`` and ``context.flagged`` lists.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        removed = []
        flagged = []

        # Unknown nodes
        if remove_unknown_nodes:
            for node in cmds.ls(type="unknown") or []:
                if dry_run:
                    flagged.append("unknown_node:{}".format(node))
                else:
                    try:
                        cmds.lockNode(node, lock=False)
                        cmds.delete(node)
                        removed.append("unknown_node:{}".format(node))
                    except Exception:
                        flagged.append("unknown_node_locked:{}".format(node))

        # Unknown plug-ins
        if remove_unknown_plugins:
            for plugin in cmds.unknownPlugin(query=True, list=True) or []:
                if dry_run:
                    flagged.append("unknown_plugin:{}".format(plugin))
                else:
                    try:
                        cmds.unknownPlugin(plugin, remove=True)
                        removed.append("unknown_plugin:{}".format(plugin))
                    except Exception:
                        flagged.append("unknown_plugin_inuse:{}".format(plugin))

        # Empty display layers
        if remove_empty_display_layers:
            for layer in cmds.ls(type="displayLayer") or []:
                if layer == "defaultLayer":
                    continue
                members = cmds.editDisplayLayerMembers(layer, query=True, fullNames=True) or []
                if not members:
                    if dry_run:
                        flagged.append("empty_display_layer:{}".format(layer))
                    else:
                        try:
                            cmds.delete(layer)
                            removed.append("empty_display_layer:{}".format(layer))
                        except Exception:
                            flagged.append("display_layer_locked:{}".format(layer))

        # Empty render layers
        if remove_empty_render_layers:
            for layer in cmds.ls(type="renderLayer") or []:
                if layer == "defaultRenderLayer":
                    continue
                members = cmds.editRenderLayerMembers(layer, query=True, fullNames=True) or []
                if not members:
                    if dry_run:
                        flagged.append("empty_render_layer:{}".format(layer))
                    else:
                        try:
                            cmds.delete(layer)
                            removed.append("empty_render_layer:{}".format(layer))
                        except Exception:
                            flagged.append("render_layer_locked:{}".format(layer))

        action_str = "dry-run" if dry_run else "cleaned"
        return maya_success(
            "Scene {} — {} items removed, {} flagged".format(action_str, len(removed), len(flagged)),
            prompt="Clean complete. Run validate_scene_for_farm to check render readiness.",
            removed=removed,
            flagged=flagged,
            removed_count=len(removed),
            flagged_count=len(flagged),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to clean scene")


def main(**kwargs):
    return clean_scene(**kwargs)


if __name__ == "__main__":
    import json

    result = clean_scene(dry_run=True)
    print(json.dumps(result))
