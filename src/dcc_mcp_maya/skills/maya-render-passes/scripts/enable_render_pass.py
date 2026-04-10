"""Enable or disable a specific render pass element."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(pass_node):
            return error_result(
                "Render pass not found: {}".format(pass_node),
                "'{}' does not exist in the scene".format(pass_node),
            ).to_dict()

        attr_candidates = ["renderable", "enabled"]
        toggled = False

        for attr in attr_candidates:
            if cmds.attributeQuery(attr, node=pass_node, exists=True):
                cmds.setAttr("{}.{}".format(pass_node, attr), int(enabled))
                toggled = True
                break

        if not toggled:
            return error_result(
                "Cannot toggle pass: {}".format(pass_node),
                "Node has neither 'renderable' nor 'enabled' attribute",
            ).to_dict()

        return success_result(
            "{} render pass '{}'".format("Enabled" if enabled else "Disabled", pass_node),
            prompt="Use list_render_passes to review all active passes.",
            pass_node=pass_node,
            enabled=enabled,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("enable_render_pass failed")
        return error_result("Failed to toggle render pass '{}'".format(pass_node), str(exc)).to_dict()


def main(**kwargs):
    return enable_render_pass(**kwargs)


if __name__ == "__main__":
    import json

    result = enable_render_pass("diffuse_pass", enabled=True)
    print(json.dumps(result))
