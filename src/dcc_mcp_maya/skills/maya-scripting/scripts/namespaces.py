"""Maya namespace management actions.

Supplements the :func:`list_namespaces` action in :mod:`references` with
full namespace lifecycle management:

- :func:`set_namespace`    — move one or more objects into a namespace
- :func:`rename_namespace` — rename an existing namespace
- :func:`delete_namespace` — delete an empty (or force-emptied) namespace
"""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

# Import built-in modules

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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        # Normalise namespace — strip leading/trailing colons
        ns = namespace.strip(":") if namespace else ""

        if ns:
            # Ensure namespace exists
            exists = cmds.namespace(exists=":{}".format(ns))
            if not exists:
                if not create_if_missing:
                    return skill_error(
                        "Namespace does not exist: {}".format(ns),
                        "Set create_if_missing=True to create it automatically",
                    )
                cmds.namespace(add=ns)

            # Move object via namespace rename (moves into ns)
            new_name = cmds.rename(object_name, "{}:{}".format(ns, object_name.split(":")[-1]))
        else:
            # Move to root namespace
            bare = object_name.split(":")[-1]
            new_name = cmds.rename(object_name, bare)

        return skill_success(
            "Moved '{}' to namespace '{}'".format(object_name, ns or ":"),
            object_name=object_name,
            namespace=ns or ":",
            new_name=new_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set namespace for '{}'".format(object_name))


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        old_ns = old_name.strip(":")
        new_ns = new_name.strip(":")

        if not old_ns:
            return skill_error("Cannot rename root namespace", "old_name must not be empty or ':'")

        if old_ns in _PROTECTED_NS:
            return skill_error(
                "Cannot rename protected namespace: {}".format(old_ns),
                "Protected namespaces: {}".format(", ".join(sorted(_PROTECTED_NS))),
            )

        if not cmds.namespace(exists=":{}".format(old_ns)):
            return skill_error(
                "Namespace does not exist: {}".format(old_ns),
                "Create the namespace first or check the name",
            )

        if cmds.namespace(exists=":{}".format(new_ns)):
            return skill_error(
                "Namespace already exists: {}".format(new_ns),
                "Choose a different new_name",
            )

        cmds.namespace(rename=[":{}".format(old_ns), new_ns])

        return skill_success(
            "Renamed namespace '{}' → '{}'".format(old_ns, new_ns),
            old_name=old_ns,
            new_name=new_ns,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to rename namespace '{}' to '{}'".format(old_name, new_name))


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
            return skill_error("Cannot delete root namespace", "namespace must not be empty or ':'")

        if ns in _PROTECTED_NS:
            return skill_error(
                "Cannot delete protected namespace: {}".format(ns),
                "Protected namespaces: {}".format(", ".join(sorted(_PROTECTED_NS))),
            )

        if not cmds.namespace(exists=":{}".format(ns)):
            return skill_error(
                "Namespace does not exist: {}".format(ns),
                "Nothing to delete",
            )

        if merge_with_root:
            cmds.namespace(removeNamespace=":{}".format(ns), mergeNamespaceWithRoot=True)
        else:
            cmds.namespace(removeNamespace=":{}".format(ns))

        return skill_success(
            "Deleted namespace '{}'".format(ns),
            namespace=ns,
            merged_with_root=merge_with_root,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete namespace '{}'".format(namespace))
