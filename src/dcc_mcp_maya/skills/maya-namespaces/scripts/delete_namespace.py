"""Delete a Maya namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Built-in namespaces that must never be modified
_PROTECTED_NS = frozenset({"UI", "shared", ":"})

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def delete_namespace(
    namespace: str,
    merge_with_root: bool = True,
) -> dict:
    """Delete a Maya namespace.

    When the namespace is not empty, objects inside it can be automatically
    moved to the root namespace before deletion by setting *merge_with_root*
    to True.

    Args:
        namespace: Namespace to delete (without leading ``":"``).
        merge_with_root: If True (default), move contained objects to the root
            namespace before deleting.  If False, raise an error when the
            namespace is not empty.

    Returns:
        ActionResultModel dict with ``context.namespace``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ns = namespace.strip(":")

        if not ns:
            return maya_error("Cannot delete root namespace", "namespace must not be empty or ':'")

        if ns in _PROTECTED_NS:
            return maya_error(
                "Cannot delete protected namespace: {}".format(ns),
                "Protected namespaces: {}".format(", ".join(sorted(_PROTECTED_NS))),
            )

        if not cmds.namespace(exists=":{}".format(ns)):
            return maya_error(
                "Namespace does not exist: {}".format(ns),
                "Nothing to delete",
            )

        if merge_with_root:
            cmds.namespace(removeNamespace=":{}".format(ns), mergeNamespaceWithRoot=True)
        else:
            cmds.namespace(removeNamespace=":{}".format(ns))

        return maya_success(
            "Deleted namespace '{}'".format(ns),
            namespace=ns,
            merged_with_root=merge_with_root,
            prompt="Check the result with list_namespaces or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete namespace '{}'".format(namespace))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_namespace`."""
    return delete_namespace(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_namespace()
    print(json.dumps(result))
