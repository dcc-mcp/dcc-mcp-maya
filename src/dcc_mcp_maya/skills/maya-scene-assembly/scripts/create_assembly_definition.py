"""Create a Maya assemblyDefinition node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_assembly_definition(name: Optional[str] = None) -> dict:
    """Create an assemblyDefinition node.

    Args:
        name: Optional name for the assembly definition node.
            Defaults to ``"assemblyDefinition1"``.

    Returns:
        ActionResultModel dict with ``context.node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        node_name = name or "assemblyDefinition1"
        node = cmds.assembly(name=node_name, type="assemblyDefinition")
        return success_result(
            "Assembly definition '{}' created".format(node),
            prompt="Definition created. Use add_assembly_representation to add LOD representations.",
            node=node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_assembly_definition failed")
        return error_result("Failed to create assembly definition", str(exc)).to_dict()


def main(**kwargs):
    return create_assembly_definition(**kwargs)


if __name__ == "__main__":
    import json
    result = create_assembly_definition("myAssembly")
    print(json.dumps(result))
