"""Create a render pass element for multi-pass compositing."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Created render pass '{}' (type={}, renderer={})".format(pass_node, pass_type, renderer),
            prompt="Use enable_render_pass to activate and set_render_pass_output to configure the output path.",
            pass_node=pass_node,
            pass_type=pass_type,
            renderer=renderer,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_render_pass failed")
        return error_result("Failed to create render pass '{}'".format(pass_type), str(exc)).to_dict()


def main(**kwargs):
    return create_render_pass(**kwargs)


if __name__ == "__main__":
    import json

    result = create_render_pass(pass_type="diffuse", name="diffuse_pass")
    print(json.dumps(result))
