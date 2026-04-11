"""Delete objects from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def delete_objects(object_names: List[str]) -> dict:
    """Delete objects from the Maya scene.

    Args:
        object_names: List of object names to delete.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not object_names:
            return skill_success(
                "No objects to delete",
                prompt="Check the result with list_primitives or use related actions to continue.",
            )
        existing = cmds.ls(object_names) or []
        if existing:
            cmds.delete(existing)
        return skill_success(
            f"Deleted {len(existing)} objects",
            deleted=existing,
            requested=object_names,
            prompt="Check the result with list_primitives or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete objects")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_objects`."""
    return delete_objects(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
