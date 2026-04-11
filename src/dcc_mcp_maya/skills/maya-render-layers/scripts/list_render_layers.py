"""List all render layers in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_render_layers(include_default: bool = True) -> dict:
    """List all render layers in the scene.

    Args:
        include_default: If True (default), include the built-in
            ``"defaultRenderLayer"`` in the result.

    Returns:
        ActionResultModel dict with ``context.layers`` — a list of dicts with
        ``name``, ``renderable``, ``member_count``, and ``is_current``.
    """

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

        return maya_success(
            "Found {} render layer(s)".format(len(layers)),
            layers=layers,
            count=len(layers),
            current_layer=current_layer,
            prompt="Use create_render_layer or add_to_render_layer to manage.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list render layers")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_render_layers`."""
    return list_render_layers(**kwargs)


if __name__ == "__main__":
    import json

    result = list_render_layers()
    print(json.dumps(result))
