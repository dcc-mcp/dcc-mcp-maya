"""Create a Maya assemblyDefinition node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional


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
        return maya_success(
            "Assembly definition '{}' created".format(node),
            prompt="Definition created. Use add_assembly_representation to add LOD representations.",
            node=node,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create assembly definition")


def main(**kwargs):
    return create_assembly_definition(**kwargs)


if __name__ == "__main__":
    import json

    result = create_assembly_definition("myAssembly")
    print(json.dumps(result))
