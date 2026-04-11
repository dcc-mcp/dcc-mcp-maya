"""Maya animation and keyframe actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def set_keyframe(
    object_name: str,
    attributes: Optional[List[str]] = None,
    time: Optional[float] = None,
    value: Optional[float] = None,
) -> dict:
    """Set a keyframe on an object at the given time.

    Args:
        object_name: Name of the object to keyframe.
        attributes: List of attribute names to key (e.g. ``["tx", "ty", "tz"]``).
            If None, keys all keyable attributes.
        time: Frame number.  Defaults to current time.
        value: Explicit value to set before keying.  Only valid when a single
            attribute is provided.

    Returns:
        ActionResultModel dict with ``context.keyframe_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        kwargs = {}  # type: Dict
        if time is not None:
            kwargs["time"] = time
        if attributes:
            kwargs["attribute"] = attributes
            if value is not None and len(attributes) == 1:
                cmds.setAttr("{}.{}".format(object_name, attributes[0]), value)

        count = cmds.setKeyframe(object_name, **kwargs)
        return success_result(
            "Set {} keyframe(s) on {}".format(count, object_name),
            object_name=object_name,
            keyframe_count=count,
            time=time,
            attributes=attributes,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_keyframe failed")
        return error_result("Failed to set keyframe on {}".format(object_name), str(exc)).to_dict()


def get_keyframes(
    object_name: str,
    attribute: Optional[str] = None,
) -> dict:
    """Get all keyframe times for an object / attribute.

    Args:
        object_name: Name of the object to query.
        attribute: Specific attribute to query (e.g. ``"tx"``).  If None,
            returns keyframes across all attributes.

    Returns:
        ActionResultModel dict with ``context.keyframes`` list of frame numbers.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        kwargs = {}  # type: Dict
        if attribute:
            kwargs["attribute"] = attribute
        raw = cmds.keyframe(object_name, query=True, timeChange=True, **kwargs)
        keyframes = list(raw) if raw else []
        return success_result(
            "Found {} keyframe(s) on {}".format(len(keyframes), object_name),
            object_name=object_name,
            attribute=attribute,
            keyframes=keyframes,
            count=len(keyframes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_keyframes failed")
        return error_result("Failed to get keyframes for {}".format(object_name), str(exc)).to_dict()


def set_timeline(
    start_frame: float = 1.0,
    end_frame: float = 120.0,
    min_frame: Optional[float] = None,
    max_frame: Optional[float] = None,
) -> dict:
    """Set the playback and animation timeline range.

    Args:
        start_frame: Playback start frame.  Default: 1.
        end_frame: Playback end frame.  Default: 120.
        min_frame: Animation range minimum (inner range).  Defaults to
            ``start_frame`` if not specified.
        max_frame: Animation range maximum (inner range).  Defaults to
            ``end_frame`` if not specified.

    Returns:
        ActionResultModel dict with timeline range info.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if min_frame is None:
            min_frame = start_frame
        if max_frame is None:
            max_frame = end_frame

        cmds.playbackOptions(
            minTime=start_frame,
            maxTime=end_frame,
            animationStartTime=min_frame,
            animationEndTime=max_frame,
        )
        return success_result(
            "Timeline set: {} - {}".format(start_frame, end_frame),
            start_frame=start_frame,
            end_frame=end_frame,
            min_frame=min_frame,
            max_frame=max_frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_timeline failed")
        return error_result("Failed to set timeline", str(exc)).to_dict()


def get_current_time() -> dict:
    """Get the current frame number.

    Returns:
        ActionResultModel dict with ``context.current_time``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        current = cmds.currentTime(query=True)
        return success_result(
            "Current time: {}".format(current),
            current_time=current,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_current_time failed")
        return error_result("Failed to get current time", str(exc)).to_dict()


def set_current_time(frame: float) -> dict:
    """Set the current frame number.

    Args:
        frame: Target frame number.

    Returns:
        ActionResultModel dict with ``context.current_time``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.currentTime(frame, update=True)
        return success_result(
            "Current time set to {}".format(frame),
            current_time=frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_current_time failed")
        return error_result("Failed to set current time", str(exc)).to_dict()


def delete_keyframes(
    object_name: str,
    attributes: Optional[List[str]] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
) -> dict:
    """Delete keyframes from an object within an optional frame range.

    Args:
        object_name: Name of the object whose keyframes will be deleted.
        attributes: List of attribute names to affect (e.g. ``["tx", "ry"]``).
            If None, all keyable attributes are targeted.
        start_frame: First frame of the range to delete.  If None and
            *end_frame* is also None, all keyframes are deleted.
        end_frame: Last frame of the range to delete.  If None and
            *start_frame* is also None, all keyframes are deleted.

    Returns:
        ActionResultModel dict with ``context.deleted_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        kwargs = {}  # type: Dict
        if attributes:
            kwargs["attribute"] = attributes
        if start_frame is not None and end_frame is not None:
            kwargs["time"] = (start_frame, end_frame)
        elif start_frame is not None:
            kwargs["time"] = (start_frame, start_frame)
        elif end_frame is not None:
            kwargs["time"] = (end_frame, end_frame)

        deleted = cmds.cutKey(object_name, clear=True, **kwargs)
        return success_result(
            "Deleted {} keyframe(s) from {}".format(deleted, object_name),
            object_name=object_name,
            deleted_count=deleted,
            attributes=attributes,
            start_frame=start_frame,
            end_frame=end_frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_keyframes failed")
        return error_result("Failed to delete keyframes from {}".format(object_name), str(exc)).to_dict()


def bake_simulation(
    objects: Optional[List[str]] = None,
    start_frame: float = 1.0,
    end_frame: float = 120.0,
    sample_by: float = 1.0,
) -> dict:
    """Bake simulation / constraints to keyframes on objects.

    Converts dynamic simulation or constraint-driven animation into explicit
    keyframes so the objects can be used independently of the rig.

    Args:
        objects: List of object names to bake.  If None, the current selection
            is used.
        start_frame: First frame of the bake range.  Default: 1.
        end_frame: Last frame of the bake range.  Default: 120.
        sample_by: Baking interval in frames (e.g. ``1.0`` = every frame,
            ``0.5`` = every half-frame).  Default: 1.

    Returns:
        ActionResultModel dict with ``context.object_count`` and frame range.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or []
        if targets:
            missing = [o for o in targets if not cmds.objExists(o)]
            if missing:
                return error_result(
                    "Objects not found: {}".format(", ".join(missing)),
                    "The following objects do not exist: {}".format(", ".join(missing)),
                ).to_dict()
            cmds.select(targets, replace=True)
        else:
            targets = cmds.ls(selection=True) or []

        if not targets:
            return error_result(
                "No objects to bake",
                "Provide object names or select objects before baking",
            ).to_dict()

        cmds.bakeSimulation(
            targets,
            time=(start_frame, end_frame),
            sampleBy=sample_by,
            simulation=True,
            preserveOutsideKeys=True,
        )
        return success_result(
            "Baked {} object(s) from frame {} to {}".format(len(targets), start_frame, end_frame),
            object_count=len(targets),
            objects=targets,
            start_frame=start_frame,
            end_frame=end_frame,
            sample_by=sample_by,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("bake_simulation failed")
        return error_result("Failed to bake simulation", str(exc)).to_dict()


def list_animation_curves(
    object_name: str,
    attribute: Optional[str] = None,
) -> dict:
    """List all animCurve nodes driving an object.

    Args:
        object_name: Name of the object to query.
        attribute: Optional specific attribute (e.g. ``"tx"``).  If None,
            all animCurve nodes connected to the object are returned.

    Returns:
        ActionResultModel dict with ``context.curves`` list of dicts
        containing ``name``, ``type``, ``key_count``, and ``attribute``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if attribute:
            plug = "{}.{}".format(object_name, attribute)
            raw_conns = cmds.listConnections(plug, source=True, destination=False, type="animCurve") or []
        else:
            raw_conns = cmds.listConnections(object_name, source=True, destination=False, type="animCurve") or []

        # Deduplicate while preserving order
        seen = set()  # type: set
        unique_curves = []  # type: List[str]
        for c in raw_conns:
            if c not in seen:
                seen.add(c)
                unique_curves.append(c)

        curves = []
        for curve in unique_curves:
            curve_type = cmds.objectType(curve)
            key_count = cmds.keyframe(curve, query=True, keyframeCount=True) or 0
            # Determine which attribute this curve drives
            driven_plugs = cmds.listConnections(curve, source=False, destination=True, plugs=True) or []
            driven_attr = driven_plugs[0].split(".")[-1] if driven_plugs else ""
            curves.append(
                {
                    "name": curve,
                    "type": curve_type,
                    "key_count": key_count,
                    "attribute": driven_attr,
                }
            )

        return success_result(
            "Found {} animCurve(s) on '{}'".format(len(curves), object_name),
            object_name=object_name,
            attribute=attribute,
            curves=curves,
            count=len(curves),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_animation_curves failed")
        return error_result("Failed to list animation curves for '{}'".format(object_name), str(exc)).to_dict()


def set_animation_curve_tangent(
    object_name: str,
    attribute: str,
    frame: Optional[float] = None,
    tangent_type: str = "auto",
    in_tangent_type: Optional[str] = None,
    out_tangent_type: Optional[str] = None,
) -> dict:
    """Set the tangent type on one or all keyframes of an animation curve.

    Args:
        object_name: Name of the animated object.
        attribute: Attribute name (e.g. ``"tx"``).
        frame: Specific frame to modify.  If None, all keys on the curve
            are updated.
        tangent_type: Tangent preset applied to both in and out tangents.
            One of ``"auto"``, ``"linear"``, ``"flat"``, ``"step"``,
            ``"spline"``, ``"clamped"``, ``"plateau"``.  Default: ``"auto"``.
            Overridden by *in_tangent_type* / *out_tangent_type* if provided.
        in_tangent_type: Override for the incoming tangent type only.
        out_tangent_type: Override for the outgoing tangent type only.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.attribute``, ``context.frame``, ``context.tangent_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_TANGENTS = ("auto", "linear", "flat", "step", "spline", "clamped", "plateau", "stepnext")

    in_type = (in_tangent_type or tangent_type).lower()
    out_type = (out_tangent_type or tangent_type).lower()

    if in_type not in _VALID_TANGENTS:
        return error_result(
            "Invalid in_tangent_type: {}".format(in_type),
            "Must be one of: {}".format(", ".join(_VALID_TANGENTS)),
        ).to_dict()
    if out_type not in _VALID_TANGENTS:
        return error_result(
            "Invalid out_tangent_type: {}".format(out_type),
            "Must be one of: {}".format(", ".join(_VALID_TANGENTS)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        plug = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(plug):
            return error_result(
                "Attribute not found: {}".format(plug),
                "'{}.{}' does not exist".format(object_name, attribute),
            ).to_dict()

        kwargs = {
            "attribute": attribute,
            "inTangentType": in_type,
            "outTangentType": out_type,
        }  # type: Dict
        if frame is not None:
            kwargs["time"] = (frame, frame)

        cmds.keyTangent(object_name, edit=True, **kwargs)

        return success_result(
            "Set tangent type on '{}.{}' (frame={})".format(object_name, attribute, frame),
            object_name=object_name,
            attribute=attribute,
            frame=frame,
            in_tangent_type=in_type,
            out_tangent_type=out_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_animation_curve_tangent failed")
        return error_result("Failed to set tangent on '{}.{}'".format(object_name, attribute), str(exc)).to_dict()


def bake_constraints(
    objects: Optional[List[str]] = None,
    start_frame: float = 1.0,
    end_frame: float = 120.0,
    sample_by: float = 1.0,
    remove_constraints: bool = False,
) -> dict:
    """Bake constraint-driven animation to explicit keyframes.

    Evaluates constraint outputs every *sample_by* frames over the given
    range and writes the resulting world-space transforms as keyframes.
    After baking the constraints can optionally be deleted.

    Args:
        objects: List of constrained transforms to bake.  Uses the current
            selection when None.
        start_frame: Start of the bake range.  Default: 1.
        end_frame: End of the bake range.  Default: 120.
        sample_by: Sampling interval in frames.  Default: 1.
        remove_constraints: If True, delete all constraints from the baked
            objects after baking.  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_count``,
        ``context.objects``, ``context.removed_constraints``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = list(objects) if objects else []
        if targets:
            missing = [o for o in targets if not cmds.objExists(o)]
            if missing:
                return error_result(
                    "Objects not found: {}".format(", ".join(missing)),
                    "The following objects do not exist: {}".format(", ".join(missing)),
                ).to_dict()
            cmds.select(targets, replace=True)
        else:
            targets = cmds.ls(selection=True) or []

        if not targets:
            return error_result(
                "No objects to bake",
                "Provide object names or select objects before baking",
            ).to_dict()

        cmds.bakeSimulation(
            targets,
            time=(start_frame, end_frame),
            sampleBy=sample_by,
            simulation=False,
            preserveOutsideKeys=True,
            disableImplicitControl=True,
            smart=False,
        )

        removed_constraints = []  # type: List[str]
        if remove_constraints:
            constraint_types = (
                "parentConstraint",
                "pointConstraint",
                "orientConstraint",
                "scaleConstraint",
                "aimConstraint",
                "geometryConstraint",
            )
            for obj in targets:
                for ctype in constraint_types:
                    constraint_nodes = cmds.listRelatives(obj, children=True, type=ctype) or []
                    for node in constraint_nodes:
                        cmds.delete(node)
                        removed_constraints.append(node)

        return success_result(
            "Baked constraints on {} object(s) from frame {} to {}".format(len(targets), start_frame, end_frame),
            object_count=len(targets),
            objects=targets,
            start_frame=start_frame,
            end_frame=end_frame,
            sample_by=sample_by,
            removed_constraints=removed_constraints,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("bake_constraints failed")
        return error_result("Failed to bake constraints", str(exc)).to_dict()


def export_animation_curves(
    object_name: str,
    file_path: str,
    attributes: Optional[List[str]] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
) -> dict:
    """Export animation curves for an object to a Maya .anim file.

    Uses ``cmds.exportEdits`` (Maya 2013+) to write a Maya ASCII or binary
    file containing only the animation curves driving *object_name*.

    Args:
        object_name: Name of the animated object.
        file_path: Output file path.  Extension determines format:
            ``".anim"`` (Maya native), ``".ma"`` (Maya ASCII),
            ``".mb"`` (Maya Binary).
        attributes: Optional list of attribute names to restrict the export.
            If ``None``, all driven attributes are exported.
        start_frame: First frame of the export range.  ``None`` = scene start.
        end_frame: Last frame of the export range.  ``None`` = scene end.

    Returns:
        ActionResultModel dict with ``context.file_path`` and
        ``context.curve_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        # Resolve frame range
        if start_frame is None:
            start_frame = cmds.playbackOptions(query=True, animationStartTime=True)
        if end_frame is None:
            end_frame = cmds.playbackOptions(query=True, animationEndTime=True)

        # Collect animCurve nodes
        anim_curves = cmds.keyframe(object_name, query=True, name=True) or []
        if attributes:
            filtered = []
            for attr in attributes:
                plug = "{}.{}".format(object_name, attr)
                curves = cmds.keyframe(plug, query=True, name=True) or []
                filtered.extend(curves)
            anim_curves = filtered

        if not anim_curves:
            return error_result(
                "No animation curves found on '{}'".format(object_name),
                "Object has no keyframe data to export",
            ).to_dict()

        # Export via cmds.select + cmds.file
        cmds.select(anim_curves, replace=True)
        export_kwargs = {
            "exportSelected": True,
            "force": True,
            "type": "mayaAscii",
        }  # type: Dict
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "ma"
        if ext == "mb":
            export_kwargs["type"] = "mayaBinary"

        cmds.file(file_path, **export_kwargs)
        cmds.select(clear=True)

        return success_result(
            "Exported {} animation curve(s) to '{}'".format(len(anim_curves), file_path),
            file_path=file_path,
            object_name=object_name,
            curve_count=len(anim_curves),
            start_frame=start_frame,
            end_frame=end_frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_animation_curves failed")
        return error_result("Failed to export animation curves for '{}'".format(object_name), str(exc)).to_dict()


def import_animation_curves(
    file_path: str,
    target_object: Optional[str] = None,
    merge: bool = True,
) -> dict:
    """Import animation curves from a file and optionally apply them to an object.

    Args:
        file_path: Path to the ``.ma`` / ``.mb`` / ``.anim`` file to import.
        target_object: Name of the object to re-target the curves onto.
            If ``None``, curves are imported as-is without re-targeting.
        merge: When ``True``, existing keys on the target are merged rather
            than replaced (``cmds.file(i=True, mergeNamespacesOnClash=True)``).

    Returns:
        ActionResultModel dict with ``context.file_path`` and
        ``context.target_object``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import os  # noqa: PLC0415

        import maya.cmds as cmds  # noqa: PLC0415

        if not os.path.isfile(file_path):
            return error_result(
                "File not found: {}".format(file_path),
                "Cannot import animation curves: path does not exist",
            ).to_dict()

        import_kwargs = {
            "i": True,
            "ignoreVersion": True,
            "mergeNamespacesOnClash": merge,
            "force": True,
        }  # type: Dict

        cmds.file(file_path, **import_kwargs)

        if target_object and cmds.objExists(target_object):
            # Copy newly imported animCurves to target by name-matching
            # (best-effort; full re-targeting requires Maya's retarget API)
            imported_curves = cmds.ls(type="animCurve") or []
            for curve in imported_curves:
                connections = cmds.listConnections(curve, destination=True, plugs=True) or []
                for conn in connections:
                    attr = conn.split(".")[-1] if "." in conn else None
                    if attr and cmds.objExists("{}.{}".format(target_object, attr)):
                        try:
                            cmds.connectAttr(
                                "{}.output".format(curve),
                                "{}.{}".format(target_object, attr),
                                force=True,
                            )
                        except Exception:
                            pass

        return success_result(
            "Imported animation curves from '{}'".format(file_path),
            file_path=file_path,
            target_object=target_object,
            merge=merge,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("import_animation_curves failed")
        return error_result("Failed to import animation curves from '{}'".format(file_path), str(exc)).to_dict()


def query_scene_time_info() -> dict:
    """Query the current scene time and playback settings as a single call.

    Returns a consolidated snapshot of all time-related scene settings:
    frame rate, animation range, playback range, and current time.

    Returns:
        ActionResultModel dict with ``context`` keys:
        ``fps``, ``animation_start``, ``animation_end``,
        ``playback_start``, ``playback_end``, ``current_time``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        fps = cmds.currentUnit(query=True, time=True)
        anim_start = cmds.playbackOptions(query=True, animationStartTime=True)
        anim_end = cmds.playbackOptions(query=True, animationEndTime=True)
        pb_start = cmds.playbackOptions(query=True, minTime=True)
        pb_end = cmds.playbackOptions(query=True, maxTime=True)
        current = cmds.currentTime(query=True)

        return success_result(
            "Scene time info retrieved",
            fps=fps,
            animation_start=anim_start,
            animation_end=anim_end,
            playback_start=pb_start,
            playback_end=pb_end,
            current_time=current,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("query_scene_time_info failed")
        return error_result("Failed to query scene time info", str(exc)).to_dict()
