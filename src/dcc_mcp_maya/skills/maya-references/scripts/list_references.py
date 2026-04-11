"""List all file references in the current scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_references() -> dict:
    """List all file references in the current scene.

    Returns:
        ActionResultModel dict with ``context.references`` — a list of dicts
        with ``reference_node``, ``file_path``, ``namespace``, and ``loaded``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} reference(s)".format(len(references)),
            references=references,
            count=len(references),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_references failed")
        return error_result("Failed to list references", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_references`."""
    return list_references(**kwargs)


if __name__ == "__main__":
    import json

    result = list_references()
    print(json.dumps(result))
