"""Enable or disable a specific render pass element."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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

        err = validate_node_exists(cmds, pass_node)
        if err:
            return err

        attr_candidates = ["renderable", "enabled"]
        toggled = False

        for attr in attr_candidates:
            if cmds.attributeQuery(attr, node=pass_node, exists=True):
                cmds.setAttr("{}.{}".format(pass_node, attr), int(enabled))
                toggled = True
                break

        if not toggled:
            return skill_error(
                "Cannot toggle pass: {}".format(pass_node),
                "Node has neither 'renderable' nor 'enabled' attribute",
            )

        return skill_success(
            "{} render pass '{}'".format("Enabled" if enabled else "Disabled", pass_node),
            prompt="Use list_render_passes to review all active passes.",
            pass_node=pass_node,
            enabled=enabled,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to toggle render pass '{}'".format(pass_node))


@skill_entry
def main(**kwargs):
    return enable_render_pass(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
