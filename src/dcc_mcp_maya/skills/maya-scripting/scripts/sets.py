"""Maya object set management actions.

Provides actions to create and manage Maya object sets (``objectSet`` nodes),
allowing an Agent to organise scene objects into named collections that can be
used for rendering, export, deformer membership, etc.
"""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional


def create_set(
    name: str,
    objects: Optional[List[str]] = None,
) -> dict:
    """Create a Maya object set.

    Args:
        name: Name for the new object set.
        objects: Optional list of objects to add immediately.
            If None or empty, an empty set is created.

    Returns:
        ActionResultModel dict with ``context.set_name`` and
        ``context.objects_added``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not name.strip():
            return maya_error("Invalid set name", "name must not be empty")

        objects_to_add = list(objects) if objects else []
        missing = [obj for obj in objects_to_add if not cmds.objExists(obj)]
        if missing:
            return maya_error(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            )

        if objects_to_add:
            set_node = cmds.sets(*objects_to_add, name=name)
        else:
            set_node = cmds.sets(name=name, empty=True)

        return maya_success(
            "Created object set '{}' with {} object(s)".format(set_node, len(objects_to_add)),
            set_name=set_node,
            objects_added=objects_to_add,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create set '{}'".format(name))


def add_to_set(
    set_name: str,
    objects: List[str],
) -> dict:
    """Add objects to an existing Maya object set.

    Args:
        set_name: Name of an existing ``objectSet`` node.
        objects: List of object names to add.

    Returns:
        ActionResultModel dict with ``context.set_name`` and
        ``context.objects_added``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return maya_error("No objects specified", "objects list must not be empty")

        if not cmds.objExists(set_name):
            return maya_error(
                "Set not found: {}".format(set_name),
                "'{}' does not exist in the scene".format(set_name),
            )

        if cmds.objectType(set_name) != "objectSet":
            return maya_error(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            )

        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return maya_error(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            )

        cmds.sets(*objects, addElement=set_name)

        return maya_success(
            "Added {} object(s) to set '{}'".format(len(objects), set_name),
            set_name=set_name,
            objects_added=list(objects),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add objects to set '{}'".format(set_name))


def remove_from_set(
    set_name: str,
    objects: List[str],
) -> dict:
    """Remove objects from an existing Maya object set.

    Args:
        set_name: Name of an existing ``objectSet`` node.
        objects: List of object names to remove.

    Returns:
        ActionResultModel dict with ``context.set_name`` and
        ``context.objects_removed``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return maya_error("No objects specified", "objects list must not be empty")

        if not cmds.objExists(set_name):
            return maya_error(
                "Set not found: {}".format(set_name),
                "'{}' does not exist in the scene".format(set_name),
            )

        if cmds.objectType(set_name) != "objectSet":
            return maya_error(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            )

        # Only attempt to remove objects that actually exist
        existing = [obj for obj in objects if cmds.objExists(obj)]
        if existing:
            cmds.sets(*existing, remove=set_name)

        removed_count = len(existing)
        skipped = [obj for obj in objects if obj not in existing]

        return maya_success(
            "Removed {} object(s) from set '{}'{}".format(
                removed_count,
                set_name,
                " ({} not found, skipped)".format(len(skipped)) if skipped else "",
            ),
            set_name=set_name,
            objects_removed=existing,
            objects_skipped=skipped,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to remove objects from set '{}'".format(set_name))


def list_sets(include_internal: bool = False) -> dict:
    """List all Maya object sets in the scene.

    Args:
        include_internal: If False (default), built-in Maya sets such as
            ``"defaultCreaseDataSet"`` or ``"defaultLightSet"`` are excluded.

    Returns:
        ActionResultModel dict with ``context.sets`` — a list of dicts with
        ``name`` and ``member_count``.
    """

    # Maya built-in default sets that clutter the result when include_internal=False
    _INTERNAL_SETS = frozenset(
        [
            "defaultCreaseDataSet",
            "defaultLightSet",
            "defaultObjectSet",
            "initialParticleSE",
            "initialShadingGroup",
        ]
    )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        all_sets = cmds.ls(type="objectSet") or []
        result = []
        for set_node in all_sets:
            if not include_internal and set_node in _INTERNAL_SETS:
                continue
            members = cmds.sets(set_node, query=True) or []
            result.append(
                {
                    "name": set_node,
                    "member_count": len(members),
                }
            )

        return maya_success(
            "Found {} object set(s)".format(len(result)),
            sets=result,
            count=len(result),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list object sets")
