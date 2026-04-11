"""Create a render pass element for multi-pass compositing."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_PASS_TYPES = {
    "beauty": "renderPassBeauty",
    "diffuse": "renderPassDiffuse",
    "specular": "renderPassSpecular",
    "shadow": "renderPassShadow",
    "ambient": "renderPassAmbient",
    "depth": "renderPassDepth",
    "normal": "renderPassNormal",
    "uv": "renderPassUV",
}


def create_render_pass(
    pass_type: str = "beauty",
    name: Optional[str] = None,
    renderer: str = "mayaSoftware",
) -> dict:
    """Create a render pass element for multi-pass compositing.

    Uses Maya's ``renderPassPlugin`` for Maya Software/Mental Ray passes,
    falling back to ``cmds.createNode("renderPass")`` for generic passes.

    Args:
        pass_type: Pass preset: ``beauty`` (default), ``diffuse``,
            ``specular``, ``shadow``, ``ambient``, ``depth``,
            ``normal``, ``uv``.
        name: Optional name for the render pass node.
        renderer: Target renderer hint (``mayaSoftware``, ``arnold``).
            For Arnold, uses ``aiAOV`` node type instead.

    Returns:
        ActionResultModel dict with ``context.pass_node`` and
        ``context.pass_type``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if renderer.lower() == "arnold":
            node_type = "aiAOV"
            node_name = name or "{}_aov".format(pass_type)
            pass_node = cmds.createNode(node_type, name=node_name)
            cmds.setAttr("{}.name".format(pass_node), pass_type, type="string")
        else:
            node_type = "renderPass"
            node_name = name or "{}_pass".format(pass_type)
            pass_node = cmds.createNode(node_type, name=node_name)
            if cmds.attributeQuery("passContribution", node=pass_node, exists=True):
                pass_contribution = _PASS_TYPES.get(pass_type, "renderPassBeauty")
                cmds.setAttr("{}.passContribution".format(pass_node), pass_contribution, type="string")

        return skill_success(
            "Created render pass '{}' (type={}, renderer={})".format(pass_node, pass_type, renderer),
            prompt="Use enable_render_pass to activate and set_render_pass_output to configure the output path.",
            pass_node=pass_node,
            pass_type=pass_type,
            renderer=renderer,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create render pass '{}'".format(pass_type))


@skill_entry
def main(**kwargs):
    return create_render_pass(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
