"""Maya object set management actions.

Provides actions to create and manage Maya object sets (``objectSet`` nodes),
allowing an Agent to organise scene objects into named collections that can be
used for rendering, export, deformer membership, etc.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not name.strip():
            return error_result("Invalid set name", "name must not be empty").to_dict()

        objects_to_add = list(objects) if objects else []
        missing = [obj for obj in objects_to_add if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            ).to_dict()

        if objects_to_add:
            set_node = cmds.sets(*objects_to_add, name=name)
        else:
            set_node = cmds.sets(name=name, empty=True)

        return success_result(
            "Created object set '{}' with {} object(s)".format(set_node, len(objects_to_add)),
            set_name=set_node,
            objects_added=objects_to_add,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_set failed")
        return error_result("Failed to create set '{}'".format(name), str(exc)).to_dict()


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return error_result("No objects specified", "objects list must not be empty").to_dict()

        if not cmds.objExists(set_name):
            return error_result(
                "Set not found: {}".format(set_name),
                "'{}' does not exist in the scene".format(set_name),
            ).to_dict()

        if cmds.objectType(set_name) != "objectSet":
            return error_result(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            ).to_dict()

        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            ).to_dict()

        cmds.sets(*objects, addElement=set_name)

        return success_result(
            "Added {} object(s) to set '{}'".format(len(objects), set_name),
            set_name=set_name,
            objects_added=list(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_to_set failed")
        return error_result("Failed to add objects to set '{}'".format(set_name), str(exc)).to_dict()


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return error_result("No objects specified", "objects list must not be empty").to_dict()

        if not cmds.objExists(set_name):
            return error_result(
                "Set not found: {}".format(set_name),
                "'{}' does not exist in the scene".format(set_name),
            ).to_dict()

        if cmds.objectType(set_name) != "objectSet":
            return error_result(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            ).to_dict()

        # Only attempt to remove objects that actually exist
        existing = [obj for obj in objects if cmds.objExists(obj)]
        if existing:
            cmds.sets(*existing, remove=set_name)

        removed_count = len(existing)
        skipped = [obj for obj in objects if obj not in existing]

        return success_result(
            "Removed {} object(s) from set '{}'{}".format(
                removed_count,
                set_name,
                " ({} not found, skipped)".format(len(skipped)) if skipped else "",
            ),
            set_name=set_name,
            objects_removed=existing,
            objects_skipped=skipped,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_from_set failed")
        return error_result("Failed to remove objects from set '{}'".format(set_name), str(exc)).to_dict()


def list_sets(include_internal: bool = False) -> dict:
    """List all Maya object sets in the scene.

    Args:
        include_internal: If False (default), built-in Maya sets such as
            ``"defaultCreaseDataSet"`` or ``"defaultLightSet"`` are excluded.

    Returns:
        ActionResultModel dict with ``context.sets`` — a list of dicts with
        ``name`` and ``member_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} object set(s)".format(len(result)),
            sets=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_sets failed")
        return error_result("Failed to list object sets", str(exc)).to_dict()
