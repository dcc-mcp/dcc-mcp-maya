"""List all Maya assembly definition and reference nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_assemblies(node_type: str = "all") -> dict:
    """List assembly nodes.

    Args:
        node_type: Filter by ``"definition"``, ``"reference"``, or ``"all"`` (default).

    Returns:
        ActionResultModel dict with ``context.definitions``, ``context.references``,
        and ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        definitions = []
        references = []

        if node_type in ("definition", "all"):
            def_nodes = cmds.ls(type="assemblyDefinition") or []
            for node in def_nodes:
                reps = cmds.assembly(node, query=True, listRepresentations=True) or []
                definitions.append(
                    {
                        "node": node,
                        "type": "assemblyDefinition",
                        "representations": reps,
                    }
                )

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
                references.append(
                    {
                        "node": node,
                        "type": "assemblyReference",
                        "active_rep": active,
                        "representations": reps,
                    }
                )

        all_nodes = definitions + references
        return skill_success(
            "Found {} assembly node(s) ({} definitions, {} references)".format(
                len(all_nodes), len(definitions), len(references)
            ),
            prompt="Use create_assembly_reference or add_assembly_representation to manage assemblies.",
            definitions=definitions,
            references=references,
            count=len(all_nodes),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list assemblies")


@skill_entry
def main(**kwargs):
    return list_assemblies(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
