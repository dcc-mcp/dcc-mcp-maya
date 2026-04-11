"""Maya scene utility actions — pivot, alignment and annotation helpers.

These actions supplement ``scene.py`` with additional scene-manipulation
helpers that are commonly needed by an AI Agent.
"""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional

def set_pivot(
    object_name: str,
    position: Optional[List[float]] = None,
    pivot_type: str = "both",
    world_space: bool = True,
) -> dict:
    """Set the rotate and/or scale pivot of a Maya object.

    Args:
        object_name: Name of the transform node whose pivot to set.
        position: World-space (or object-space when ``world_space=False``)
            XYZ coordinates ``[x, y, z]``.  If None, no position change is
            applied and only *pivot_type* validation is performed.
        pivot_type: Which pivot to set — ``"rotate"``, ``"scale"``, or
            ``"both"`` (default).
        world_space: If True (default), interpret *position* in world space.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.position``, ``context.pivot_type``.
    """

    _VALID_PIVOT_TYPES = ("rotate", "scale", "both")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if pivot_type not in _VALID_PIVOT_TYPES:
            return maya_error(
                "Invalid pivot_type: {}".format(pivot_type),
                "pivot_type must be one of {}".format(_VALID_PIVOT_TYPES),
            )

        if position is not None:
            if len(position) != 3:
                return maya_error(
                    "Invalid position: {}".format(position),
                    "position must be a list of exactly 3 floats [x, y, z]",
                )

            px, py, pz = float(position[0]), float(position[1]), float(position[2])
            space_flag = {"worldSpace": True} if world_space else {}

            if pivot_type in ("rotate", "both"):
                cmds.xform(object_name, rotatePivot=[px, py, pz], **space_flag)
            if pivot_type in ("scale", "both"):
                cmds.xform(object_name, scalePivot=[px, py, pz], **space_flag)

        # Read back the actual pivot position
        rp = list(cmds.xform(object_name, query=True, rotatePivot=True, worldSpace=True))
        sp = list(cmds.xform(object_name, query=True, scalePivot=True, worldSpace=True))

        return maya_success(
            "Set pivot on '{}' ({})".format(object_name, pivot_type),
            object_name=object_name,
            pivot_type=pivot_type,
            rotate_pivot=rp,
            scale_pivot=sp,
            world_space=world_space,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to set pivot on '{}'".format(object_name))

def align_objects(
    objects: List[str],
    axis: str = "x",
    mode: str = "center",
    reference: Optional[str] = None,
) -> dict:
    """Align a list of objects along a given world-space axis.

    Each object's translate component along *axis* is set so that its
    bounding-box minimum, center, or maximum coincides with the reference
    value.  By default the reference value is derived from the bounding box
    of all provided objects combined; alternatively a specific *reference*
    object can be specified.

    Args:
        objects: List of object names to align (minimum 2).
        axis: World-space axis to align along — ``"x"``, ``"y"``, or ``"z"``.
            Default: ``"x"``.
        mode: Alignment mode — ``"min"`` (align left/bottom/front edges),
            ``"center"`` (align centres, default), or ``"max"`` (align
            right/top/back edges).
        reference: Optional name of a reference object whose bounding-box
            value on *axis* is used as the target.  If None, the combined
            bounding box of all *objects* is used.

    Returns:
        ActionResultModel dict with ``context.objects``, ``context.axis``,
        ``context.mode``, ``context.target_value``.
    """

    _VALID_AXES = ("x", "y", "z")
    _VALID_MODES = ("min", "center", "max")
    _AXIS_INDEX = {"x": 0, "y": 1, "z": 2}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects or len(objects) < 2:
            return maya_error(
                "Insufficient objects",
                "align_objects requires at least 2 objects",
            )

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return maya_error(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            )

        mode_lower = mode.lower()
        if mode_lower not in _VALID_MODES:
            return maya_error(
                "Invalid mode: {}".format(mode),
                "mode must be one of {}".format(_VALID_MODES),
            )

        # Validate all objects exist
        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return maya_error(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            )

        idx = _AXIS_INDEX[axis_lower]

        if reference:
            if not cmds.objExists(reference):
                return maya_error(
                    "Reference object not found: {}".format(reference),
                    "'{}' does not exist".format(reference),
                )
            ref_bb = cmds.exactWorldBoundingBox(reference)
            # bb = [xmin, ymin, zmin, xmax, ymax, zmax]
            if mode_lower == "min":
                target_value = ref_bb[idx]
            elif mode_lower == "max":
                target_value = ref_bb[idx + 3]
            else:
                target_value = (ref_bb[idx] + ref_bb[idx + 3]) / 2.0
        else:
            # Combined bounding box
            all_bb = [cmds.exactWorldBoundingBox(obj) for obj in objects]
            combined_min = min(bb[idx] for bb in all_bb)
            combined_max = max(bb[idx + 3] for bb in all_bb)
            if mode_lower == "min":
                target_value = combined_min
            elif mode_lower == "max":
                target_value = combined_max
            else:
                target_value = (combined_min + combined_max) / 2.0

        translate_attr = {"x": "tx", "y": "ty", "z": "tz"}[axis_lower]
        aligned = []
        for obj in objects:
            bb = cmds.exactWorldBoundingBox(obj)
            obj_min = bb[idx]
            obj_max = bb[idx + 3]
            if mode_lower == "min":
                obj_ref = obj_min
            elif mode_lower == "max":
                obj_ref = obj_max
            else:
                obj_ref = (obj_min + obj_max) / 2.0

            current_t = cmds.getAttr("{}.{}".format(obj, translate_attr))
            delta = target_value - obj_ref
            cmds.setAttr("{}.{}".format(obj, translate_attr), current_t + delta)
            aligned.append(obj)

        return maya_success(
            "Aligned {} object(s) along {} axis ({} mode)".format(len(aligned), axis_lower, mode_lower),
            objects=aligned,
            axis=axis_lower,
            mode=mode_lower,
            target_value=target_value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to align objects")

def create_annotation(
    object_name: str,
    text: str,
    position: Optional[List[float]] = None,
) -> dict:
    """Create a Maya annotation node attached to an object.

    Annotations are text labels that float in the viewport and are linked to
    a specific object via an *annotationShape* node.

    Args:
        object_name: The transform node to annotate.
        text: The annotation text to display.
        position: Optional world-space XYZ offset for the annotation text
            ``[x, y, z]``.  Defaults to slightly above the object's pivot.

    Returns:
        ActionResultModel dict with ``context.annotation_transform``,
        ``context.object_name``, ``context.text``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if not text:
            return maya_error(
                "Empty annotation text",
                "text must be a non-empty string",
            )

        # Determine annotation position
        if position is not None:
            if len(position) != 3:
                return maya_error(
                    "Invalid position: {}".format(position),
                    "position must be a list of exactly 3 floats [x, y, z]",
                )
            ann_pos = [float(v) for v in position]
        else:
            # Default: slightly above the object pivot
            pivot = cmds.xform(object_name, query=True, rotatePivot=True, worldSpace=True)
            ann_pos = [pivot[0], pivot[1] + 1.0, pivot[2]]

        ann_transform = cmds.annotate(object_name, text=text, point=ann_pos)
        # annotate() returns the shape node; get its parent transform
        ann_parent = cmds.listRelatives(ann_transform, parent=True, fullPath=False)
        ann_transform_name = ann_parent[0] if ann_parent else ann_transform

        return maya_success(
            "Created annotation '{}' on '{}'".format(text, object_name),
            annotation_transform=ann_transform_name,
            annotation_shape=ann_transform,
            object_name=object_name,
            text=text,
            position=ann_pos,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to create annotation on '{}'".format(object_name))

def set_object_color(
    object_name: str,
    color_index: int,
    use_default: bool = False,
) -> dict:
    """Set the wireframe color of a Maya object by index.

    Maya's viewport wireframe colour can be overridden per-object using a
    colour index (0 = default/yellow, 1–31 = custom palette entries).

    Args:
        object_name: Name of the transform to colour.
        color_index: Maya colour index (0–31).  Index 0 restores the
            default colour (same as ``use_default=True``).
        use_default: When True, disable the colour override and restore the
            default wireframe colour.  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.color_index``, ``context.use_default``.
    """

    if not (0 <= color_index <= 31):
        return maya_error(
            "Invalid color_index: {}".format(color_index),
            "color_index must be between 0 and 31",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if use_default or color_index == 0:
            cmds.setAttr("{}.overrideEnabled".format(object_name), False)
            cmds.setAttr("{}.overrideColor".format(object_name), 0)
            effective_index = 0
        else:
            cmds.setAttr("{}.overrideEnabled".format(object_name), True)
            cmds.setAttr("{}.overrideColor".format(object_name), color_index)
            effective_index = color_index

        return maya_success(
            "Set wireframe color on '{}' to index {}".format(object_name, effective_index),
            object_name=object_name,
            color_index=effective_index,
            use_default=use_default,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to set object color on '{}'".format(object_name))

def toggle_gpu_override(
    object_name: str,
    enabled: bool = True,
) -> dict:
    """Toggle the GPU override display mode on a polygon mesh.

    Maya's GPU cache override (``gpuCacheSupportedTypes`` / hardware
    ``displayMode``) is set via the transform's ``overrideDisplayType``
    attribute.  When *enabled* is True the object uses a bounding-box (2)
    display type to hint the GPU path; set False to restore normal (0).

    Note: This is a lightweight approximation for environments without a
    full GPU cache plug-in.  It exposes the ``overrideEnabled`` /
    ``overrideDisplayType`` attributes that are available on every Maya node.

    Args:
        object_name: Transform or shape node name.
        enabled: True to enable GPU override display (bounding box mode),
            False to restore normal display.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.enabled``, ``context.display_type``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if enabled:
            # 2 = bounding box display type
            cmds.setAttr("{}.overrideEnabled".format(object_name), True)
            cmds.setAttr("{}.overrideDisplayType".format(object_name), 2)
            display_type = 2
        else:
            cmds.setAttr("{}.overrideEnabled".format(object_name), False)
            cmds.setAttr("{}.overrideDisplayType".format(object_name), 0)
            display_type = 0

        return maya_success(
            "{} GPU override on '{}'".format("Enabled" if enabled else "Disabled", object_name),
            object_name=object_name,
            enabled=enabled,
            display_type=display_type,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to toggle GPU override on '{}'".format(object_name))

def create_polygon_text(
    text: str,
    name: Optional[str] = None,
    font: str = "Arial",
    depth: float = 0.5,
    extrude: bool = True,
) -> dict:
    """Create a 3D polygon text object in the scene.

    Uses ``cmds.textCurves`` to generate text curves and then extrudes them
    with ``cmds.extrude`` to produce a solid polygon mesh.

    Args:
        text: The text string to create.
        name: Optional name for the resulting group/transform node.
        font: Font name recognised by Maya (e.g. ``"Arial"``, ``"Courier"``).
            Default: ``"Arial"``.
        depth: Extrusion depth for the 3D effect.  Default: 0.5.
        extrude: If True, extrude text curves into a 3D polygon mesh.
            If False, the raw NURBS text curves are returned.

    Returns:
        ActionResultModel dict with ``context.objects`` (list of created
        transform names) and ``context.text``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not text:
            return maya_error("Empty text", "text parameter must not be empty")

        kwargs = {"font": font, "text": text}
        if name:
            kwargs["name"] = name

        # Create text curves
        curves = cmds.textCurves(**kwargs) or []

        objects = list(curves)

        if extrude and curves:
            # Extrude each NURBS curve sub-component to polygon
            extruded = []
            for crv in curves:
                try:
                    ex = cmds.extrude(crv, extrudeType=0, length=depth, constructionHistory=False)
                    extruded.extend(ex or [])
                except Exception:
                    extruded.append(crv)
            objects = extruded

        return maya_success(
            "Created polygon text: '{}'".format(text),
            text=text,
            font=font,
            depth=depth if extrude else None,
            extruded=extrude,
            objects=objects,
            count=len(objects),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to create polygon text '{}'".format(text))

def set_shading_mode(
    mode: str = "smooth",
    panel: Optional[str] = None,
) -> dict:
    """Set the viewport shading mode for the active or specified panel.

    Changes how geometry is displayed in Maya's model view panels.

    Available modes:
    - ``"wireframe"`` — wireframe only (no shading)
    - ``"smooth"`` — smooth shaded (default, no textures)
    - ``"textured"`` — smooth shaded with texture display
    - ``"flat"`` — flat shaded polygons
    - ``"bounding_box"`` — bounding box only (fastest)

    Args:
        mode: Target display mode.  Default: ``"smooth"``.
        panel: Name of the model panel to affect (e.g. ``"modelPanel1"``).
            If None, uses the first model panel found via ``cmds.getPanel``.

    Returns:
        ActionResultModel dict with ``context.mode``, ``context.panel``.
    """

    _MODE_MAP = {
        "wireframe": ("wireframeOnShaded", False),
        "smooth": ("smoothShaded", False),
        "textured": ("textured", True),
        "flat": ("flatShaded", False),
        "bounding_box": ("boundingBox", False),
    }

    mode_lower = mode.lower()
    if mode_lower not in _MODE_MAP:
        return maya_error(
            "Invalid mode: {}".format(mode),
            "mode must be one of {}".format(sorted(_MODE_MAP.keys())),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Resolve target panel
        if panel:
            if not cmds.modelPanel(panel, query=True, exists=True):
                return maya_error(
                    "Panel not found: {}".format(panel),
                    "'{}' is not a valid model panel".format(panel),
                )
            target_panel = panel
        else:
            panels = cmds.getPanel(type="modelPanel") or []
            if not panels:
                return maya_error(
                    "No model panels found",
                    "Could not locate any Maya model view panel",
                )
            target_panel = panels[0]

        # Apply the shading mode
        if mode_lower == "wireframe":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="wireframe", displayTextures=False)
        elif mode_lower == "smooth":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="smoothShaded", displayTextures=False)
        elif mode_lower == "textured":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="smoothShaded", displayTextures=True)
        elif mode_lower == "flat":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="flatShaded", displayTextures=False)
        elif mode_lower == "bounding_box":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="boundingBox", displayTextures=False)

        return maya_success(
            "Set shading mode to '{}' on panel '{}'".format(mode_lower, target_panel),
            mode=mode_lower,
            panel=target_panel,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to set shading mode")
