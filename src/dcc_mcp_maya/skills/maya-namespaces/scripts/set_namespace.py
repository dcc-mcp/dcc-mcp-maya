"""Move a Maya object into a namespace."""

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


def main(**kwargs):
    return set_namespace(**kwargs)


if __name__ == "__main__":
    import json

    result = set_namespace()
    print(json.dumps(result))
