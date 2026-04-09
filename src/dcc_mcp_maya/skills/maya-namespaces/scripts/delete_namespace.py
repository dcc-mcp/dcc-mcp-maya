"""Delete a Maya namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

# Built-in namespaces that must never be modified
_PROTECTED_NS = frozenset({"UI", "shared", ":"})


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ns = namespace.strip(":")

        if not ns:
            return error_result("Cannot delete root namespace", "namespace must not be empty or ':'").to_dict()

        if ns in _PROTECTED_NS:
            return error_result(
                "Cannot delete protected namespace: {}".format(ns),
                "Protected namespaces: {}".format(", ".join(sorted(_PROTECTED_NS))),
            ).to_dict()

        if not cmds.namespace(exists=":{}".format(ns)):
            return error_result(
                "Namespace does not exist: {}".format(ns),
                "Nothing to delete",
            ).to_dict()

        if merge_with_root:
            cmds.namespace(removeNamespace=":{}".format(ns), mergeNamespaceWithRoot=True)
        else:
            cmds.namespace(removeNamespace=":{}".format(ns))

        return success_result(
            "Deleted namespace '{}'".format(ns),
            namespace=ns,
            merged_with_root=merge_with_root,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_namespace failed")
        return error_result("Failed to delete namespace '{}'".format(namespace), str(exc)).to_dict()


def main(**kwargs):
    return delete_namespace(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_namespace()
    print(json.dumps(result))
