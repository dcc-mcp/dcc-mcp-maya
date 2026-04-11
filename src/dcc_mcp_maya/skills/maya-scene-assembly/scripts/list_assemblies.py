"""List all Maya assembly definition and reference nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_assemblies(node_type: str = "all") -> dict:
    """List assembly nodes.

    Args:
        node_type: Filter by ``"definition"``, ``"reference"``, or ``"all"`` (default).

    Returns:
        ActionResultModel dict with ``context.definitions``, ``context.references``,
        and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        definitions = []
        references = []

        if node_type in ("definition", "all"):
            def_nodes = cmds.ls(type="assemblyDefinition") or []
            for node in def_nodes:
                reps = cmds.assembly(node, query=True, listRepresentations=True) or []
                definitions.append({
                    "node": node,
                    "type": "assemblyDefinition",
                    "representations": reps,
                })

        if node_type in ("reference", "all"):
            ref_nodes = cmds.ls(type="assemblyReference") or []
            for node in ref_nodes:
                try:
                    active = cmds.assembly(node, query=True, active=True) or ""
                except Exception:
                    active = ""
                try:
                    reps = cmds.assembly(node, query=True, listRepresentations=True) or []
                except Exception:
                    reps = []
                references.append({
                    "node": node,
                    "type": "assemblyReference",
                    "active_rep": active,
                    "representations": reps,
                })

        all_nodes = definitions + references
        return success_result(
            "Found {} assembly node(s) ({} definitions, {} references)".format(
                len(all_nodes), len(definitions), len(references)
            ),
            prompt="Use create_assembly_reference or add_assembly_representation to manage assemblies.",
            definitions=definitions,
            references=references,
            count=len(all_nodes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_assemblies failed")
        return error_result("Failed to list assemblies", str(exc)).to_dict()


def main(**kwargs):
    return list_assemblies(**kwargs)


if __name__ == "__main__":
    import json
    result = list_assemblies()
    print(json.dumps(result))
