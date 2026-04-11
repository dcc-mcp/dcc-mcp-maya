"""Move a Maya object into a namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Built-in namespaces that must never be modified
_PROTECTED_NS = frozenset({"UI", "shared", ":"})

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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
            return maya_error(
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
                    return maya_error(
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

        return maya_success(
            "Moved '{}' to namespace '{}'".format(object_name, ns or ":"),
            object_name=object_name,
            namespace=ns or ":",
            new_name=new_name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set namespace for '{}'".format(object_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_namespace`."""
    return set_namespace(**kwargs)

if __name__ == "__main__":
    import json

    result = set_namespace()
    print(json.dumps(result))
