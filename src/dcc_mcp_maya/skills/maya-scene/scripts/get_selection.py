"""Return the current Maya selection."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import make_scene_object


def get_selection(include_transform: bool = False) -> dict:
    """Return the current Maya selection.

    Returns :class:`~dcc_mcp_core.SceneObject`-compatible dicts for
    cross-DCC interoperability.

    Args:
        include_transform: If True, include translate/rotate/scale in
            each object entry.

    Returns:
        ActionResultModel dict with ``context.selection`` list and
        ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        selected = cmds.ls(selection=True, long=True) or []
        result = []
        for long_name in selected:
            obj = make_scene_object(cmds, long_name, include_transform=include_transform)
            result.append(obj)

        return skill_success(
            "{} objects selected".format(len(result)),
            selection=result,
            count=len(result),
            prompt="Use set_transform to modify or assign_material to shade selected objects.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get selection")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_selection`."""
    return get_selection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
