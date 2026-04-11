"""Create a render layer and optionally add objects to it."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional


def create_render_layer(
    name: str,
    objects: Optional[List[str]] = None,
    make_current: bool = False,
) -> dict:
    """Create a render layer and optionally add objects to it.

    Args:
        name: Name for the new render layer.
        objects: Optional list of objects to add to the layer.
            If None or empty, the layer is created empty.
        make_current: If True, switch to the new layer after creation.
            Default: False.

    Returns:
        ActionResultModel dict with ``context.layer_name``,
        ``context.objects_added``, and ``context.is_current``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not name.strip():
            return maya_error("Invalid layer name", "name must not be empty")

        objects_to_add = list(objects) if objects else []
        missing = [obj for obj in objects_to_add if not cmds.objExists(obj)]
        if missing:
            return maya_error(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            )

        if objects_to_add:
            layer = cmds.createRenderLayer(*objects_to_add, name=name, number=1, makeCurrent=make_current)
        else:
            layer = cmds.createRenderLayer(name=name, number=1, empty=True, makeCurrent=make_current)

        return maya_success(
            "Created render layer '{}' with {} object(s)".format(layer, len(objects_to_add)),
            layer_name=layer,
            objects_added=objects_to_add,
            is_current=make_current,
            prompt="Use add_to_render_layer to populate or set_render_layer_attribute to adjust.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create render layer '{}'".format(name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_render_layer`."""
    return create_render_layer(**kwargs)


if __name__ == "__main__":
    import json

    result = create_render_layer()
    print(json.dumps(result))
