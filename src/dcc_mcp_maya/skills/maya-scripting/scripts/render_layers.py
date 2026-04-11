"""Maya render layer management actions.

Provides actions to create, populate and list legacy render layers
(``renderLayer`` nodes) so an Agent can control per-layer render settings
and object membership.

Note: Maya 2022+ ships with the newer *Render Setup* system (``renderSetup``).
These actions target the legacy system exposed via ``cmds.createRenderLayer``
and ``cmds.editRenderLayerMembers`` which is available in all supported Maya
versions (2020 – 2025).
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not name.strip():
            return error_result("Invalid layer name", "name must not be empty").to_dict()

        objects_to_add = list(objects) if objects else []
        missing = [obj for obj in objects_to_add if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            ).to_dict()

        if objects_to_add:
            layer = cmds.createRenderLayer(*objects_to_add, name=name, number=1, makeCurrent=make_current)
        else:
            layer = cmds.createRenderLayer(name=name, number=1, empty=True, makeCurrent=make_current)

        return success_result(
            "Created render layer '{}' with {} object(s)".format(layer, len(objects_to_add)),
            layer_name=layer,
            objects_added=objects_to_add,
            is_current=make_current,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_render_layer failed")
        return error_result("Failed to create render layer '{}'".format(name), str(exc)).to_dict()


def set_render_layer(
    object_name: str,
    layer_name: str,
) -> dict:
    """Assign an object to an existing render layer.

    Args:
        object_name: Name of the object to assign.
        layer_name: Name of the target render layer.

    Returns:
        ActionResultModel dict with ``context.object_name`` and
        ``context.layer_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if not cmds.objExists(layer_name):
            return error_result(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        if cmds.objectType(layer_name) != "renderLayer":
            return error_result(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}', expected 'renderLayer'".format(layer_name, cmds.objectType(layer_name)),
            ).to_dict()

        cmds.editRenderLayerMembers(layer_name, object_name, noRecurse=True)

        return success_result(
            "Assigned '{}' to render layer '{}'".format(object_name, layer_name),
            object_name=object_name,
            layer_name=layer_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_render_layer failed")
        return error_result(
            "Failed to assign '{}' to render layer '{}'".format(object_name, layer_name),
            str(exc),
        ).to_dict()


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


def delete_render_layer(layer_name: str) -> dict:
    """Delete a render layer from the scene.

    The built-in ``defaultRenderLayer`` cannot be deleted.  Any objects that
    were members of the layer are moved back to the default render layer
    automatically by Maya.

    Args:
        layer_name: Name of the render layer to delete.

    Returns:
        ActionResultModel dict with ``context.layer_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if layer_name == "defaultRenderLayer":
            return error_result(
                "Cannot delete defaultRenderLayer",
                "The defaultRenderLayer is protected and cannot be removed",
            ).to_dict()

        if not cmds.objExists(layer_name):
            return error_result(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        if cmds.objectType(layer_name) != "renderLayer":
            return error_result(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}'".format(layer_name, cmds.objectType(layer_name)),
            ).to_dict()

        # Switch to defaultRenderLayer if this is the current layer
        current = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)
        if current == layer_name:
            cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")

        cmds.delete(layer_name)

        return success_result(
            "Deleted render layer '{}'".format(layer_name),
            layer_name=layer_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_render_layer failed")
        return error_result("Failed to delete render layer '{}'".format(layer_name), str(exc)).to_dict()


def set_render_layer_attribute(
    layer_name: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute override on a render layer node.

    Common attributes:
    - ``renderable`` (bool): whether the layer is included in batch render
    - ``color`` (list of 3 floats): layer identification colour in the UI

    Args:
        layer_name: Name of the render layer to modify.
        attribute: Attribute name on the ``renderLayer`` node.
        value: New value.  Scalar or list-of-3 floats for compound attrs.

    Returns:
        ActionResultModel dict with ``context.layer_name``,
        ``context.attribute``, and ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(layer_name):
            return error_result(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        if cmds.objectType(layer_name) != "renderLayer":
            return error_result(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}'".format(layer_name, cmds.objectType(layer_name)),
            ).to_dict()

        attr_path = "{}.{}".format(layer_name, attribute)

        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value, type="double3" if len(value) == 3 else "double4")
        elif isinstance(value, bool):
            cmds.setAttr(attr_path, int(value))
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(layer_name, attribute, value),
            layer_name=layer_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_render_layer_attribute failed")
        return error_result("Failed to set attribute '{}.{}'".format(layer_name, attribute), str(exc)).to_dict()
