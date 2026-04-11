"""Remove objects from an existing Maya object set."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
            return skill_error("No objects specified", "objects list must not be empty")

        if not cmds.objExists(set_name):
            return skill_error(
                "Set not found: {}".format(set_name),
                "'{}' does not exist in the scene".format(set_name),
            )

        if cmds.objectType(set_name) != "objectSet":
            return skill_error(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            )

        # Only attempt to remove objects that actually exist
        existing = [obj for obj in objects if cmds.objExists(obj)]
        if existing:
            cmds.sets(*existing, remove=set_name)

        removed_count = len(existing)
        skipped = [obj for obj in objects if obj not in existing]

        return skill_success(
            "Removed {} object(s) from set '{}'{}".format(
                removed_count,
                set_name,
                " ({} not found, skipped)".format(len(skipped)) if skipped else "",
            ),
            set_name=set_name,
            objects_removed=existing,
            objects_skipped=skipped,
            prompt="Use list_set_members to verify removal.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to remove objects from set '{}'".format(set_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_from_set`."""
    return remove_from_set(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
