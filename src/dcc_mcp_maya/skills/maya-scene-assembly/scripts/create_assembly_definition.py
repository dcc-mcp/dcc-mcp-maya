"""Create a Maya assemblyDefinition node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_assembly_definition(name: Optional[str] = None) -> dict:
    """Create an assemblyDefinition node.

    Args:
        name: Optional name for the assembly definition node.
            Defaults to ``"assemblyDefinition1"``.

    Returns:
        ActionResultModel dict with ``context.node``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        node_name = name or "assemblyDefinition1"
        node = cmds.assembly(name=node_name, type="assemblyDefinition")
        return skill_success(
            "Assembly definition '{}' created".format(node),
            prompt="Definition created. Use add_assembly_representation to add LOD representations.",
            node=node,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create assembly definition")


@skill_entry
def main(**kwargs):
    return create_assembly_definition(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
