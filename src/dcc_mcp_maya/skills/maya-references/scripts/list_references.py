"""List all file references in the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_references() -> dict:
    """List all file references in the current scene.

    Returns:
        ActionResultModel dict with ``context.references`` — a list of dicts
        with ``reference_node``, ``file_path``, ``namespace``, and ``loaded``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ref_nodes = cmds.ls(type="reference") or []
        # Filter out the built-in sharedReferenceNode
        ref_nodes = [r for r in ref_nodes if r != "sharedReferenceNode"]

        references = []
        for ref_node in ref_nodes:
            try:
                file_path = cmds.referenceQuery(ref_node, filename=True, withoutCopyNumber=True)
                namespace = cmds.referenceQuery(ref_node, namespace=True, shortName=True)
                loaded = cmds.referenceQuery(ref_node, isLoaded=True)
            except Exception:
                continue
            references.append(
                {
                    "reference_node": ref_node,
                    "file_path": file_path,
                    "namespace": namespace,
                    "loaded": loaded,
                }
            )

        return skill_success(
            "Found {} reference(s)".format(len(references)),
            references=references,
            count=len(references),
            prompt="Use reload_reference or remove_reference to manage the listed entries.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list references")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_references`."""
    return list_references(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
