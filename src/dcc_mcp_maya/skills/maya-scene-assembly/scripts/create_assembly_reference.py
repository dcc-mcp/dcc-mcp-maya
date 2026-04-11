"""Create an assemblyReference node that instances an assembly definition."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not definition:
        return error_result(
            "Missing parameter",
            "'definition' is required — provide an assembly definition node name or file path.",
        ).to_dict()

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

        return success_result(
            "Assembly reference '{}' created".format(ref_node),
            prompt="Reference instantiated. Use list_assemblies to manage LOD switching.",
            ref_node=ref_node,
            definition=definition,
            active_rep=active_rep or "",
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_assembly_reference failed")
        return error_result("Failed to create assembly reference", str(exc)).to_dict()


def main(**kwargs):
    return create_assembly_reference(**kwargs)


if __name__ == "__main__":
    import json
    result = create_assembly_reference("myAssembly")
    print(json.dumps(result))
