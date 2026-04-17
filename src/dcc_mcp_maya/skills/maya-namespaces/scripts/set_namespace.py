"""Move a Maya object into a namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Built-in namespaces that must never be modified
_PROTECTED_NS = frozenset({"UI", "shared", ":"})

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success  # noqa: E402

from dcc_mcp_maya.api import validate_node_exists  # noqa: E402


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
        ToolResult dict with ``context.object_name``,
        ``context.namespace``, ``context.new_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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
            prompt="Check the result with list_namespaces or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set namespace for '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_namespace`."""
    return set_namespace(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
