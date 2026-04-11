"""Enable or disable a specific render pass element."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def enable_render_pass(
    pass_node: str,
    enabled: bool = True,
) -> dict:
    """Enable or disable a render pass element.

    Args:
        pass_node: Name of the renderPass or aiAOV node.
        enabled: True to enable the pass, False to disable.  Default: True.

    Returns:
        ActionResultModel dict with ``context.pass_node`` and
        ``context.enabled``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(pass_node):
            return maya_error(
                "Render pass not found: {}".format(pass_node),
                "'{}' does not exist in the scene".format(pass_node),
            )

        attr_candidates = ["renderable", "enabled"]
        toggled = False

        for attr in attr_candidates:
            if cmds.attributeQuery(attr, node=pass_node, exists=True):
                cmds.setAttr("{}.{}".format(pass_node, attr), int(enabled))
                toggled = True
                break

        if not toggled:
            return maya_error(
                "Cannot toggle pass: {}".format(pass_node),
                "Node has neither 'renderable' nor 'enabled' attribute",
            )

        return maya_success(
            "{} render pass '{}'".format("Enabled" if enabled else "Disabled", pass_node),
            prompt="Use list_render_passes to review all active passes.",
            pass_node=pass_node,
            enabled=enabled,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to toggle render pass '{}'".format(pass_node))

def main(**kwargs):
    return enable_render_pass(**kwargs)

if __name__ == "__main__":
    import json

    result = enable_render_pass("diffuse_pass", enabled=True)
    print(json.dumps(result))
