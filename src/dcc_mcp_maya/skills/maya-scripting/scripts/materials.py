"""Maya material creation and assignment actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def create_material(
    shader_type: str = "lambert",
    name: Optional[str] = None,
) -> dict:
    """Create a Maya shading material.

    Args:
        shader_type: Shader node type.  Supported: ``lambert``, ``blinn``,
            ``phong``, ``phongE``, ``aiStandardSurface``.  Default: ``lambert``.
        name: Optional name for the created material.

    Returns:
        ActionResultModel dict with ``context.material_name`` and
        ``context.shading_group``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        mat = cmds.shadingNode(shader_type, asShader=True)
        if name:
            mat = cmds.rename(mat, name)
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}_SG".format(mat))
        cmds.connectAttr("{}.outColor".format(mat), "{}.surfaceShader".format(sg), force=True)
        return success_result(
            "Created material: {}".format(mat),
            material_name=mat,
            shader_type=shader_type,
            shading_group=sg,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_material failed")
        return error_result("Failed to create material", str(exc)).to_dict()


def assign_material(material_name: str, objects: List[str]) -> dict:
    """Assign a material to one or more objects.

    Args:
        material_name: Name of the shading group **or** the material node.
        objects: List of mesh/transform object names.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Accept either SG or material name
        if cmds.objectType(material_name) != "shadingEngine":
            connections = cmds.listConnections(
                "{}.outColor".format(material_name),
                type="shadingEngine",
            )
            if not connections:
                return error_result(
                    "No shading group found for '{}'".format(material_name),
                    "Connect material to a shading group first or use assign_material with the SG name",
                ).to_dict()
            sg = connections[0]
        else:
            sg = material_name

        existing = cmds.ls(objects)
        if not existing:
            return error_result(
                "No objects found",
                "None of the requested objects exist: {}".format(objects),
            ).to_dict()

        cmds.sets(existing, edit=True, forceElement=sg)
        return success_result(
            "Assigned '{}' to {} object(s)".format(sg, len(existing)),
            shading_group=sg,
            objects=existing,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("assign_material failed")
        return error_result("Failed to assign material", str(exc)).to_dict()


def set_material_attribute(
    material_name: str,
    attribute: str,
    value: Any,
) -> dict:
    """Set an attribute on a material node.

    Args:
        material_name: Name of the material node.
        attribute: Attribute name (e.g. ``"color"``, ``"transparency"``).
        value: New value.  Scalar, list-of-3 (RGB), or list-of-4 (RGBA).

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material_name):
            return error_result(
                "Material not found: {}".format(material_name),
                "'{}' does not exist".format(material_name),
            ).to_dict()

        attr_path = "{}.{}".format(material_name, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value, type="double3" if len(value) == 3 else "double4")
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(material_name, attribute, value),
            material_name=material_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_material_attribute failed")
        return error_result("Failed to set material attribute", str(exc)).to_dict()


def list_materials(shader_type: Optional[str] = None) -> dict:
    """List all material nodes in the scene.

    Args:
        shader_type: Optional filter by shader type (e.g. ``"lambert"``).

    Returns:
        ActionResultModel dict with ``context.materials`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if shader_type:
            materials = cmds.ls(type=shader_type) or []
        else:
            all_shaders = []
            for st in _SUPPORTED_SHADERS:
                all_shaders.extend(cmds.ls(type=st) or [])
            # Also catch any user-created materials not in known list
            all_shaders.extend(cmds.ls(materials=True) or [])
            # Deduplicate preserving order
            seen = set()  # type: ignore[var-annotated]
            materials = []  # type: List[str]
            for m in all_shaders:
                if m not in seen:
                    seen.add(m)
                    materials.append(m)

        return success_result(
            "Found {} material(s)".format(len(materials)),
            materials=materials,
            count=len(materials),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_materials failed")
        return error_result("Failed to list materials", str(exc)).to_dict()


def get_shader_assignment(object_name: str) -> dict:
    """Query which shader (material) is assigned to an object or face set.

    Args:
        object_name: Transform or mesh node name, or a face component
            (e.g. ``"pCube1"`` or ``"pCube1.f[0:5]"``).

    Returns:
        ActionResultModel dict with ``context.shading_groups`` — a list of
        dicts with ``shading_group`` and ``material`` keys.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        # Resolve shading engines connected to the shape(s)
        shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True) or []
        if not shapes:
            # Might already be a shape or component
            shapes = [object_name]

        shading_groups = []
        seen_sgs = set()  # type: ignore[var-annotated]

        for shape in shapes:
            sgs = cmds.listConnections(shape, type="shadingEngine") or []
            for sg in sgs:
                if sg in seen_sgs:
                    continue
                seen_sgs.add(sg)
                # Find surface shader connected to this SG
                shaders = cmds.listConnections("{}.surfaceShader".format(sg)) or []
                material = shaders[0] if shaders else ""
                shading_groups.append({"shading_group": sg, "material": material})

        return success_result(
            "Found {} shading group(s) on '{}'".format(len(shading_groups), object_name),
            object_name=object_name,
            shading_groups=shading_groups,
            count=len(shading_groups),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_shader_assignment failed")
        return error_result("Failed to get shader assignment for '{}'".format(object_name), str(exc)).to_dict()


def get_material_connections(material_name: str) -> dict:
    """List all nodes connected to a material (textures, utilities, etc.).

    Returns the full set of incoming connections to every attribute on the
    material node, which lets an Agent understand the complete shading network.

    Args:
        material_name: Name of the material node to inspect.

    Returns:
        ActionResultModel dict with ``context.connections`` — a list of dicts
        with ``source_node``, ``source_attr``, ``dest_attr``, ``node_type``
        keys, and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material_name):
            return error_result(
                "Material not found: {}".format(material_name),
                "'{}' does not exist in the scene".format(material_name),
            ).to_dict()

        # List all source plugs connected into this material
        raw_connections = (
            cmds.listConnections(
                material_name,
                source=True,
                destination=False,
                connections=True,
                plugs=True,
            )
            or []
        )

        # listConnections with connections=True returns pairs: [dest, src, dest, src, …]
        connections = []
        i = 0
        while i + 1 < len(raw_connections):
            dest_plug = raw_connections[i]
            src_plug = raw_connections[i + 1]
            # dest_plug is "material.attr"; src_plug is "node.attr"
            dest_attr = dest_plug.split(".", 1)[-1] if "." in dest_plug else dest_plug
            src_parts = src_plug.split(".", 1)
            src_node = src_parts[0]
            src_attr = src_parts[1] if len(src_parts) > 1 else ""
            node_type = cmds.nodeType(src_node) if cmds.objExists(src_node) else "unknown"
            connections.append(
                {
                    "source_node": src_node,
                    "source_attr": src_attr,
                    "dest_attr": dest_attr,
                    "node_type": node_type,
                }
            )
            i += 2

        return success_result(
            "Found {} connection(s) into material '{}'".format(len(connections), material_name),
            material_name=material_name,
            connections=connections,
            count=len(connections),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_material_connections failed")
        return error_result("Failed to get connections for material '{}'".format(material_name), str(exc)).to_dict()


def list_shading_groups() -> dict:
    """List all shading engine (shadingEngine) nodes in the current scene.

    Provides a scene-level view of every shading group, including the
    assigned surface shader and the number of members.

    Returns:
        ActionResultModel dict with ``context.shading_groups`` — a list of
        dicts with ``name``, ``surface_shader``, ``shader_type``,
        ``member_count`` keys, and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        sgs = cmds.ls(type="shadingEngine") or []
        result = []
        for sg in sgs:
            shaders = cmds.listConnections("{}.surfaceShader".format(sg)) or []
            surface_shader = shaders[0] if shaders else ""
            shader_type = cmds.nodeType(surface_shader) if surface_shader else ""
            try:
                members = cmds.sets(sg, query=True) or []
                member_count = len(members)
            except Exception:
                member_count = 0
            result.append(
                {
                    "name": sg,
                    "surface_shader": surface_shader,
                    "shader_type": shader_type,
                    "member_count": member_count,
                }
            )

        return success_result(
            "Found {} shading group(s)".format(len(result)),
            shading_groups=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_shading_groups failed")
        return error_result("Failed to list shading groups", str(exc)).to_dict()


def reset_to_default_material(object_name: str) -> dict:
    """Assign the built-in ``lambert1`` (initialShadingGroup) to an object.

    This effectively resets the object to Maya's default material, removing
    any previously assigned custom material.

    Args:
        object_name: Transform or mesh node name to reset.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        cmds.sets(object_name, edit=True, forceElement="initialShadingGroup")

        return success_result(
            "Reset '{}' to default material (lambert1)".format(object_name),
            object_name=object_name,
            shading_group="initialShadingGroup",
            material="lambert1",
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("reset_to_default_material failed")
        return error_result("Failed to reset material for '{}'".format(object_name), str(exc)).to_dict()
