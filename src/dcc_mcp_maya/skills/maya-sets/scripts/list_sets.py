"""List all Maya object sets in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


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

        return skill_success(
            "Found {} object set(s)".format(len(result)),
            sets=result,
            count=len(result),
            prompt="Use add_to_set or delete_set to manage the listed sets.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list object sets")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_sets`."""
    return list_sets(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
