"""Apply a gamma correction node to a texture."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def apply_gamma_correction(
    texture_node: str,
    gamma: float = 2.2,
    name: Optional[str] = None,
) -> dict:
    """Apply a Maya ``gammaCorrect`` node to a texture.

    Inserts a ``gammaCorrect`` utility node between a file texture and its
    downstream connections.  Useful for manually correcting color space when
    full OCIO color management is not in use.

    Args:
        texture_node: Name of the file texture (``file``) node.
        gamma: Gamma value to apply uniformly to R, G, B channels.
            Use ``2.2`` to linearise sRGB textures, or ``0.4545`` for the
            reverse (linear → sRGB).
        name: Optional name for the ``gammaCorrect`` node.

    Returns:
        ActionResultModel dict with ``context.gamma_node`` and
        ``context.texture_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(texture_node):
            return error_result(
                "Texture node not found: {}".format(texture_node),
                "'{}' does not exist in the scene".format(texture_node),
            ).to_dict()

        node_type = cmds.objectType(texture_node)
        if node_type != "file":
            return error_result(
                "Expected a 'file' texture node, got '{}'".format(node_type),
                "Provide the file texture node name (not the shading group).",
            ).to_dict()

        kwargs = {}
        if name:
            kwargs["name"] = name
        gamma_node = cmds.createNode("gammaCorrect", **kwargs)

        cmds.setAttr("{}.gamma".format(gamma_node), gamma, gamma, gamma, type="double3")

        cmds.connectAttr(
            "{}.outColor".format(texture_node),
            "{}.value".format(gamma_node),
            force=True,
        )

        return success_result(
            "Applied gamma {} to '{}'".format(gamma, texture_node),
            prompt="Connect {}.outValue to a material's color attribute.".format(gamma_node),
            gamma_node=gamma_node,
            texture_node=texture_node,
            gamma=gamma,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("apply_gamma_correction failed")
        return error_result("Failed to apply gamma correction", str(exc)).to_dict()


def main(**kwargs):
    return apply_gamma_correction(**kwargs)


if __name__ == "__main__":
    import json

    result = apply_gamma_correction("file1", gamma=2.2)
    print(json.dumps(result))
