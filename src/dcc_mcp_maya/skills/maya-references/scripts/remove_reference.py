"""Remove a file reference from the current scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def remove_reference(
    reference_node: str,
    remove_namespace: bool = True,
) -> dict:
    """Remove a file reference from the current scene.

    Args:
        reference_node: Name of the reference node to remove (e.g.
            ``"characterRN"``).  Use :func:`list_references` to discover
            available reference nodes.
        remove_namespace: If True (default), also delete the namespace that was
            created for this reference after removal.

    Returns:
        ActionResultModel dict with ``context.reference_node`` and
        ``context.namespace_removed``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return error_result(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist in the scene".format(reference_node),
            ).to_dict()

        if cmds.objectType(reference_node) != "reference":
            return error_result(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}', expected 'reference'".format(reference_node, cmds.objectType(reference_node)),
            ).to_dict()

        # Resolve namespace before removal
        namespace_removed = ""
        if remove_namespace:
            try:
                namespace_removed = cmds.referenceQuery(reference_node, namespace=True, shortName=True)
            except Exception:
                namespace_removed = ""

        cmds.file(referenceNode=reference_node, removeReference=True)

        # Remove the namespace if it still exists
        if remove_namespace and namespace_removed:
            try:
                if cmds.namespace(exists=namespace_removed):
                    cmds.namespace(removeNamespace=namespace_removed, mergeNamespaceWithRoot=True)
            except Exception:
                pass

        return success_result(
            "Removed reference '{}'".format(reference_node),
            reference_node=reference_node,
            namespace_removed=namespace_removed if remove_namespace else "",
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_reference failed")
        return error_result("Failed to remove reference '{}'".format(reference_node), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_reference`."""
    return remove_reference(**kwargs)


if __name__ == "__main__":
    import json

    result = remove_reference()
    print(json.dumps(result))
