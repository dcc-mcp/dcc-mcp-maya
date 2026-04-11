"""List all render layers in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_render_layers(include_default: bool = True) -> dict:
    """List all render layers in the scene.

    Args:
        include_default: If True (default), include the built-in
            ``"defaultRenderLayer"`` in the result.

    Returns:
        ActionResultModel dict with ``context.layers`` — a list of dicts with
        ``name``, ``renderable``, ``member_count``, and ``is_current``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        layer_nodes = cmds.ls(type="renderLayer") or []
        current_layer = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)

        layers = []
        for layer in layer_nodes:
            if not include_default and layer == "defaultRenderLayer":
                continue
            try:
                members = cmds.editRenderLayerMembers(layer, query=True, fullNames=True) or []
                renderable = bool(cmds.getAttr("{}.renderable".format(layer)))
            except Exception:
                members = []
                renderable = False
            layers.append(
                {
                    "name": layer,
                    "renderable": renderable,
                    "member_count": len(members),
                    "is_current": layer == current_layer,
                }
            )

        return success_result(
            "Found {} render layer(s)".format(len(layers)),
            layers=layers,
            count=len(layers),
            current_layer=current_layer,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_render_layers failed")
        return error_result("Failed to list render layers", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_render_layers`."""
    return list_render_layers(**kwargs)


if __name__ == "__main__":
    import json

    result = list_render_layers()
    print(json.dumps(result))
