"""Remove a file reference from the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return skill_error(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist in the scene".format(reference_node),
            )

        if cmds.objectType(reference_node) != "reference":
            return skill_error(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}', expected 'reference'".format(reference_node, cmds.objectType(reference_node)),
            )

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

        return skill_success(
            "Removed reference '{}'".format(reference_node),
            reference_node=reference_node,
            namespace_removed=namespace_removed if remove_namespace else "",
            prompt="Use list_references to verify removal.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to remove reference '{}'".format(reference_node))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_reference`."""
    return remove_reference(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
