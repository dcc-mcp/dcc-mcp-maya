"""Create an assemblyReference node that instances an assembly definition."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_assembly_reference(
    definition: str,
    name: Optional[str] = None,
    active_rep: Optional[str] = None,
) -> dict:
    """Create an assemblyReference from a definition.

    Args:
        definition: Assembly definition node or ``.ma``/``.mb`` file path.
        name: Optional name for the reference node.
        active_rep: Optional name of the initial active representation.

    Returns:
        ActionResultModel dict with ``context.ref_node`` and ``context.definition``.
    """

    if not definition:
        return skill_error(
            "Missing parameter",
            "'definition' is required — provide an assembly definition node name or file path.",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ref_name = name or "assemblyReference1"
        ref_node = cmds.assembly(name=ref_name, type="assemblyReference")

        try:
            cmds.setAttr("{}.definition".format(ref_node), definition, type="string")
        except Exception:
            pass

        if active_rep:
            try:
                cmds.assembly(ref_node, edit=True, active=active_rep)
            except Exception:
                pass

        return skill_success(
            "Assembly reference '{}' created".format(ref_node),
            prompt="Reference instantiated. Use list_assemblies to manage LOD switching.",
            ref_node=ref_node,
            definition=definition,
            active_rep=active_rep or "",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create assembly reference")


@skill_entry
def main(**kwargs):
    return create_assembly_reference(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
