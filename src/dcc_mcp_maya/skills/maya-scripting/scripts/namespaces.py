"""Maya namespace management actions.

Supplements the :func:`list_namespaces` action in :mod:`references` with
full namespace lifecycle management:

- :func:`set_namespace`    — move one or more objects into a namespace
- :func:`rename_namespace` — rename an existing namespace
- :func:`delete_namespace` — delete an empty (or force-emptied) namespace
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

# Built-in namespaces that must never be modified
_PROTECTED_NS = frozenset({"UI", "shared", ":"})


def set_namespace(
    object_name: str,
    namespace: str,
    create_if_missing: bool = True,
) -> dict:
    """Move a Maya object into a namespace.

    Args:
        object_name: Name of the object to move (without namespace prefix).
        namespace: Target namespace (without leading ``":"``).  Use an empty
            string ``""`` or ``":"`` to move the object to the root namespace.
        create_if_missing: If True, create the namespace when it does not yet
            exist.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.namespace``, ``context.new_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        # Normalise namespace — strip leading/trailing colons
        ns = namespace.strip(":") if namespace else ""

        if ns:
            # Ensure namespace exists
            exists = cmds.namespace(exists=":{}".format(ns))
            if not exists:
                if not create_if_missing:
                    return error_result(
                        "Namespace does not exist: {}".format(ns),
                        "Set create_if_missing=True to create it automatically",
                    ).to_dict()
                cmds.namespace(add=ns)

            # Move object via namespace rename (moves into ns)
            new_name = cmds.rename(object_name, "{}:{}".format(ns, object_name.split(":")[-1]))
        else:
            # Move to root namespace
            bare = object_name.split(":")[-1]
            new_name = cmds.rename(object_name, bare)

        return success_result(
            "Moved '{}' to namespace '{}'".format(object_name, ns or ":"),
            object_name=object_name,
            namespace=ns or ":",
            new_name=new_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_namespace failed")
        return error_result("Failed to set namespace for '{}'".format(object_name), str(exc)).to_dict()


def rename_namespace(
    old_name: str,
    new_name: str,
) -> dict:
    """Rename an existing Maya namespace.

    Args:
        old_name: Current namespace name (without leading ``":"``).
        new_name: Desired new namespace name (without leading ``":"``).

    Returns:
        ActionResultModel dict with ``context.old_name``,
        ``context.new_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        old_ns = old_name.strip(":")
        new_ns = new_name.strip(":")

        if not old_ns:
            return error_result("Cannot rename root namespace", "old_name must not be empty or ':'").to_dict()

        if old_ns in _PROTECTED_NS:
            return error_result(
                "Cannot rename protected namespace: {}".format(old_ns),
                "Protected namespaces: {}".format(", ".join(sorted(_PROTECTED_NS))),
            ).to_dict()

        if not cmds.namespace(exists=":{}".format(old_ns)):
            return error_result(
                "Namespace does not exist: {}".format(old_ns),
                "Create the namespace first or check the name",
            ).to_dict()

        if cmds.namespace(exists=":{}".format(new_ns)):
            return error_result(
                "Namespace already exists: {}".format(new_ns),
                "Choose a different new_name",
            ).to_dict()

        cmds.namespace(rename=[":{}".format(old_ns), new_ns])

        return success_result(
            "Renamed namespace '{}' → '{}'".format(old_ns, new_ns),
            old_name=old_ns,
            new_name=new_ns,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("rename_namespace failed")
        return error_result("Failed to rename namespace '{}' to '{}'".format(old_name, new_name), str(exc)).to_dict()


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
