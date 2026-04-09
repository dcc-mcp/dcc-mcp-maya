"""Maya scene management actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def new_scene(force: bool = False) -> dict:
    """Create a new Maya scene.

    Args:
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(new=True, force=force)
        return success_result("New scene created").to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("new_scene failed")
        return error_result("Failed to create new scene", str(exc)).to_dict()


def save_scene(file_path: Optional[str] = None, file_type: str = "mayaBinary") -> dict:
    """Save the current Maya scene.

    Args:
        file_path: Destination path.  If None, saves to the current file path.
        file_type: ``"mayaBinary"`` (default) or ``"mayaAscii"``.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if file_path:
            cmds.file(rename=file_path)
        saved = cmds.file(save=True, type=file_type)
        return success_result(
            f"Scene saved to {saved}",
            file_path=saved,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("save_scene failed")
        return error_result("Failed to save scene", str(exc)).to_dict()


def open_scene(file_path: str, force: bool = False) -> dict:
    """Open a Maya scene file.

    Args:
        file_path: Path to the .ma / .mb file.
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(file_path, open=True, force=force)
        return success_result(
            f"Opened scene: {file_path}",
            file_path=file_path,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("open_scene failed")
        return error_result(f"Failed to open {file_path}", str(exc)).to_dict()


def list_objects(object_type: Optional[str] = None, dag: bool = True) -> dict:
    """List objects in the current Maya scene.

    Args:
        object_type: Optional Maya type filter (e.g. ``"mesh"``, ``"transform"``).
        dag: If True, only return DAG nodes.

    Returns:
        ActionResultModel dict with ``context.objects`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"dag": dag}
        if object_type:
            kwargs["type"] = object_type
        objects = cmds.ls(**kwargs) or []
        return success_result(
            f"Found {len(objects)} objects",
            objects=objects,
            count=len(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_objects failed")
        return error_result("Failed to list objects", str(exc)).to_dict()


def get_selection() -> dict:
    """Return the current Maya selection.

    Returns:
        ActionResultModel dict with ``context.selection`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        selection = cmds.ls(selection=True) or []
        return success_result(
            f"{len(selection)} objects selected",
            selection=selection,
            count=len(selection),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_selection failed")
        return error_result("Failed to get selection", str(exc)).to_dict()


def set_selection(objects: List[str]) -> dict:
    """Set the active Maya selection.

    Args:
        objects: List of object names to select.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.select(objects, replace=True)
        return success_result(
            f"Selected {len(objects)} objects",
            selection=objects,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_selection failed")
        return error_result("Failed to set selection", str(exc)).to_dict()


def group_objects(objects: List[str], group_name: Optional[str] = None, world: bool = False) -> dict:
    """Group a list of objects under a new group node.

    Args:
        objects: List of object names to group.
        group_name: Optional name for the new group node.
        world: If True, the group is parented to the world (root level).

    Returns:
        ActionResultModel dict with ``context.group_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return error_result("No objects provided", "objects list must not be empty").to_dict()

        existing = cmds.ls(objects) or []
        if not existing:
            return error_result(
                "No objects found",
                "None of the requested objects exist: {}".format(objects),
            ).to_dict()

        kwargs = {}  # type: dict
        if world:
            kwargs["world"] = True
        grp = cmds.group(existing, **kwargs)
        if group_name:
            grp = cmds.rename(grp, group_name)

        return success_result(
            "Grouped {} object(s) into '{}'".format(len(existing), grp),
            group_name=grp,
            objects=existing,
            count=len(existing),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("group_objects failed")
        return error_result("Failed to group objects", str(exc)).to_dict()


def parent_object(child: str, parent: Optional[str] = None, world: bool = False) -> dict:
    """Set or clear the parent of an object.

    Args:
        child: Name of the object to re-parent.
        parent: Name of the new parent.  If None and *world* is True, the
            object is parented to the world (un-parented).
        world: If True, parent the object to the world regardless of *parent*.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(child):
            return error_result(
                "Child not found: {}".format(child),
                "'{}' does not exist in the scene".format(child),
            ).to_dict()

        if world or parent is None:
            cmds.parent(child, world=True)
            return success_result(
                "Parented '{}' to world".format(child),
                child=child,
                parent=None,
            ).to_dict()

        if not cmds.objExists(parent):
            return error_result(
                "Parent not found: {}".format(parent),
                "'{}' does not exist in the scene".format(parent),
            ).to_dict()

        cmds.parent(child, parent)
        return success_result(
            "Parented '{}' under '{}'".format(child, parent),
            child=child,
            parent=parent,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("parent_object failed")
        return error_result("Failed to parent '{}'" .format(child), str(exc)).to_dict()


def select_by_type(object_type: str) -> dict:
    """Select all objects of a given Maya type.

    Args:
        object_type: Maya node type string (e.g. ``"mesh"``, ``"transform"``,
            ``"joint"``, ``"camera"``).

    Returns:
        ActionResultModel dict with ``context.selection`` and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        objects = cmds.ls(type=object_type) or []
        if objects:
            cmds.select(objects, replace=True)
        else:
            cmds.select(clear=True)

        return success_result(
            "Selected {} '{}' object(s)".format(len(objects), object_type),
            object_type=object_type,
            selection=objects,
            count=len(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("select_by_type failed")
        return error_result("Failed to select by type '{}'".format(object_type), str(exc)).to_dict()


def get_session_info() -> dict:
    """Return Maya version, scene path, and basic stats.

    Returns:
        ActionResultModel dict with version, scene, fps information.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        info = {
            "maya_version": cmds.about(version=True),
            "api_version": cmds.about(apiVersion=True),
            "scene_file": cmds.file(query=True, sceneName=True) or "<unsaved>",
            "scene_modified": cmds.file(query=True, modified=True),
            "fps": cmds.currentUnit(query=True, time=True),
            "up_axis": cmds.upAxis(query=True, axis=True),
            "object_count": len(cmds.ls(dag=True) or []),
        }
        return success_result("Maya session info", **info).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_session_info failed")
        return error_result("Failed to get session info", str(exc)).to_dict()


def duplicate_object(
    object_name: str,
    new_name: Optional[str] = None,
    instance: bool = False,
) -> dict:
    """Duplicate an object in the Maya scene.

    Args:
        object_name: Name of the object to duplicate.
        new_name: Optional name for the duplicated object.
        instance: If True, create an instance instead of a full copy.

    Returns:
        ActionResultModel dict with ``context.object_name`` of the new object.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        result = cmds.duplicate(object_name, instanceLeaf=instance, returnRootsOnly=True)
        new_obj = result[0]
        if new_name:
            new_obj = cmds.rename(new_obj, new_name)

        return success_result(
            "Duplicated '{}' as '{}'".format(object_name, new_obj),
            object_name=new_obj,
            source=object_name,
            instance=instance,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("duplicate_object failed")
        return error_result("Failed to duplicate '{}'".format(object_name), str(exc)).to_dict()


def freeze_transforms(object_name: str) -> dict:
    """Freeze (apply) the transforms of an object.

    Zeroes out translate/rotate and sets scale to 1 by baking current
    transform values into the shape.

    Args:
        object_name: Name of the object whose transforms to freeze.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        cmds.makeIdentity(object_name, apply=True, translate=True, rotate=True, scale=True)
        return success_result(
            "Transforms frozen on '{}'".format(object_name),
            object_name=object_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("freeze_transforms failed")
        return error_result("Failed to freeze transforms on '{}'".format(object_name), str(exc)).to_dict()


def center_pivot(object_name: str) -> dict:
    """Center the pivot point of an object to its bounding box center.

    Args:
        object_name: Name of the object.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        cmds.xform(object_name, centerPivots=True)
        pivot = list(cmds.xform(object_name, query=True, worldSpace=True, pivots=True))
        return success_result(
            "Pivot centered on '{}'".format(object_name),
            object_name=object_name,
            pivot=pivot,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("center_pivot failed")
        return error_result("Failed to center pivot on '{}'".format(object_name), str(exc)).to_dict()


def get_bounding_box(object_name: str) -> dict:
    """Query the world-space bounding box of an object.

    Args:
        object_name: Name of the object to query.

    Returns:
        ActionResultModel dict with ``context.min``, ``context.max``,
        ``context.center``, and ``context.size``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        bb = cmds.exactWorldBoundingBox(object_name)
        # bb = [xmin, ymin, zmin, xmax, ymax, zmax]
        bb_min = [bb[0], bb[1], bb[2]]
        bb_max = [bb[3], bb[4], bb[5]]
        center = [(bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0]
        size = [bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]]
        return success_result(
            "Bounding box of '{}'".format(object_name),
            object_name=object_name,
            min=bb_min,
            max=bb_max,
            center=center,
            size=size,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_bounding_box failed")
        return error_result("Failed to get bounding box of '{}'".format(object_name), str(exc)).to_dict()


def set_visibility(object_name: str, visible: bool) -> dict:
    """Show or hide an object.

    Args:
        object_name: Name of the object to show/hide.
        visible: True to show, False to hide.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        cmds.setAttr("{}.visibility".format(object_name), 1 if visible else 0)
        state = "visible" if visible else "hidden"
        return success_result(
            "'{}' is now {}".format(object_name, state),
            object_name=object_name,
            visible=visible,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_visibility failed")
        return error_result("Failed to set visibility on '{}'".format(object_name), str(exc)).to_dict()


def lock_object(object_name: str, lock: bool = True) -> dict:
    """Lock or unlock the transform attributes of an object.

    When locked, translate/rotate/scale channels cannot be edited.

    Args:
        object_name: Name of the object.
        lock: True to lock, False to unlock.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        _LOCK_ATTRS = [
            "translateX", "translateY", "translateZ",
            "rotateX", "rotateY", "rotateZ",
            "scaleX", "scaleY", "scaleZ",
        ]
        for attr in _LOCK_ATTRS:
            cmds.setAttr("{}.{}".format(object_name, attr), lock=lock)

        state = "locked" if lock else "unlocked"
        return success_result(
            "Transform attributes {} on '{}'".format(state, object_name),
            object_name=object_name,
            locked=lock,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("lock_object failed")
        return error_result("Failed to {} '{}'".format("lock" if lock else "unlock", object_name), str(exc)).to_dict()


def get_scene_info(include_transforms: bool = True) -> dict:
    """Return a hierarchical DAG description of the current scene.

    For each DAG transform node the result includes the node's name, type,
    direct parent and immediate children so callers can reconstruct the full
    hierarchy without additional queries.

    Args:
        include_transforms: If True (default), each node entry also carries its
            world-space translate/rotate/scale values.

    Returns:
        ActionResultModel dict with ``context.nodes`` (list of dicts) and
        ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        transforms = cmds.ls(type="transform", long=True) or []
        nodes = []
        for long_name in transforms:
            short_name = long_name.split("|")[-1]
            node = {
                "name": short_name,
                "long_name": long_name,
                "type": cmds.objectType(long_name),
                "parent": (cmds.listRelatives(long_name, parent=True, fullPath=True) or [None])[0],
                "children": cmds.listRelatives(long_name, children=True, fullPath=True) or [],
            }
            if include_transforms:
                node["translate"] = list(cmds.getAttr("{}.translate".format(long_name))[0])
                node["rotate"] = list(cmds.getAttr("{}.rotate".format(long_name))[0])
                node["scale"] = list(cmds.getAttr("{}.scale".format(long_name))[0])
            nodes.append(node)

        return success_result(
            "Scene info: {} transform node(s)".format(len(nodes)),
            nodes=nodes,
            count=len(nodes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_scene_info failed")
        return error_result("Failed to get scene info", str(exc)).to_dict()


def export_scene(file_path: str, file_type: str = "mayaBinary") -> dict:
    """Export the entire current scene to a file.

    Unlike :func:`export_selection` (which exports only selected objects),
    this function exports the complete scene.

    Args:
        file_path: Destination path including file extension.
        file_type: Maya export type string.  Common values:
            ``"mayaBinary"`` (default), ``"mayaAscii"``, ``"FBX export"``.

    Returns:
        ActionResultModel dict with ``context.file_path`` and
        ``context.file_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(rename=file_path)
        saved = cmds.file(save=True, type=file_type, force=True)
        return success_result(
            "Scene exported to {}".format(saved),
            file_path=saved,
            file_type=file_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_scene failed")
        return error_result("Failed to export scene to '{}'".format(file_path), str(exc)).to_dict()


def set_frame_rate(fps: str = "film") -> dict:
    """Change the scene's playback frame rate.

    Args:
        fps: A Maya time-unit string or numeric alias.  Common values:

            * ``"game"``  – 15 fps
            * ``"film"``  – 24 fps  *(default)*
            * ``"pal"``   – 25 fps
            * ``"ntsc"``  – 30 fps
            * ``"show"``  – 48 fps
            * ``"palf"``  – 50 fps
            * ``"ntscf"`` – 60 fps

    Returns:
        ActionResultModel dict with ``context.fps`` (the applied setting).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_FPS = {"game", "film", "pal", "ntsc", "show", "palf", "ntscf",
                  "23.976fps", "29.97fps", "47.952fps", "59.94fps",
                  "44100fps", "48000fps"}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if fps not in _VALID_FPS:
            return error_result(
                "Invalid frame rate: '{}'".format(fps),
                "Valid values: {}".format(", ".join(sorted(_VALID_FPS))),
            ).to_dict()

        cmds.currentUnit(time=fps)
        actual = cmds.currentUnit(query=True, time=True)
        return success_result(
            "Frame rate set to '{}'".format(actual),
            fps=actual,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_frame_rate failed")
        return error_result("Failed to set frame rate to '{}'".format(fps), str(exc)).to_dict()


def list_cameras(include_default: bool = True) -> dict:
    """List all cameras in the scene with their basic attributes.

    Args:
        include_default: If True (default), includes Maya's built-in cameras
            (``persp``, ``top``, ``front``, ``side``).  Set to False to return
            only user-created cameras.

    Returns:
        ActionResultModel dict with ``context.cameras`` (list of dicts) and
        ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _DEFAULT_CAMERAS = {"persp", "top", "front", "side",
                        "perspShape", "topShape", "frontShape", "sideShape"}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        camera_shapes = cmds.ls(type="camera") or []
        cameras = []
        for shape in camera_shapes:
            transform = (cmds.listRelatives(shape, parent=True) or [shape])[0]
            if not include_default and transform in _DEFAULT_CAMERAS:
                continue
            cam = {
                "name": transform,
                "shape": shape,
                "focal_length": cmds.getAttr("{}.focalLength".format(shape)),
                "near_clip": cmds.getAttr("{}.nearClipPlane".format(shape)),
                "far_clip": cmds.getAttr("{}.farClipPlane".format(shape)),
                "renderable": cmds.getAttr("{}.renderable".format(shape)),
            }
            cameras.append(cam)

        return success_result(
            "Found {} camera(s)".format(len(cameras)),
            cameras=cameras,
            count=len(cameras),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_cameras failed")
        return error_result("Failed to list cameras", str(exc)).to_dict()


def create_locator(name: Optional[str] = None, position: Optional[List[float]] = None) -> dict:
    """Create a Maya locator node.

    Locators are non-renderable helper nodes commonly used as position markers,
    aim targets, or constraint targets.

    Args:
        name: Optional name for the locator's transform node.  If None, Maya
            generates a default name (``"locator1"``, etc.).
        position: Optional ``[x, y, z]`` world-space position.  If None, the
            locator is created at the origin.

    Returns:
        ActionResultModel dict with ``context.object_name`` and
        ``context.position``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.spaceLocator(name=name) if name else cmds.spaceLocator()
        loc_transform = result[0]

        if position and len(position) == 3:
            cmds.move(position[0], position[1], position[2], loc_transform)

        pos = position or [0.0, 0.0, 0.0]
        return success_result(
            "Created locator '{}'".format(loc_transform),
            object_name=loc_transform,
            position=pos,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_locator failed")
        return error_result("Failed to create locator", str(exc)).to_dict()


_ACTIONS = [
    ("new_scene", "Create a new Maya scene", "scene", ["scene", "new"]),
    ("save_scene", "Save the current Maya scene", "scene", ["scene", "save", "io"]),
    ("open_scene", "Open a Maya scene file", "scene", ["scene", "open", "io"]),
    ("list_objects", "List objects in the current Maya scene", "scene", ["list", "query"]),
    ("get_selection", "Return the current Maya selection", "scene", ["selection", "query"]),
    ("set_selection", "Set the active Maya selection", "scene", ["selection"]),
    ("get_session_info", "Return Maya version, scene path, and basic stats", "scene", ["session", "info", "query"]),
    ("group_objects", "Group a list of objects under a new group node", "scene", ["group", "hierarchy"]),
    ("parent_object", "Set or clear the parent of an object", "scene", ["parent", "hierarchy"]),
    ("select_by_type", "Select all objects of a given Maya type", "scene", ["selection", "type", "query"]),
    ("duplicate_object", "Duplicate an object in the Maya scene", "scene", ["duplicate", "copy"]),
    ("freeze_transforms", "Freeze the transforms of an object", "scene", ["transform", "freeze"]),
    ("center_pivot", "Center the pivot point of an object to its bounding box center", "scene", ["pivot", "transform"]),
    ("get_bounding_box", "Query the world-space bounding box of an object", "scene", ["bounding_box", "query"]),
    ("set_visibility", "Show or hide an object", "scene", ["visibility", "display"]),
    ("lock_object", "Lock or unlock the transform attributes of an object", "scene", ["lock", "transform"]),
    ("get_scene_info", "Return a hierarchical DAG description of the current scene", "scene", ["scene", "info", "query", "hierarchy"]),
    ("export_scene", "Export the entire current scene to a file", "scene", ["export", "io"]),
    ("set_frame_rate", "Change the scene playback frame rate", "scene", ["fps", "time", "settings"]),
    ("list_cameras", "List all cameras in the scene", "scene", ["camera", "list", "query"]),
    ("create_locator", "Create a Maya locator node", "scene", ["locator", "helper", "create"]),
]
