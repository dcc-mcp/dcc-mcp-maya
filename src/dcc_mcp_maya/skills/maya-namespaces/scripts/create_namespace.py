"""Create a new namespace in Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def create_namespace(
    name: str,
    parent: str = ":",
    set_as_current: bool = False,
) -> dict:
    """Create a new namespace.

    Args:
        name: The namespace name to create (e.g. ``"char_hero"``).
        parent: Parent namespace path.  Use ``":"`` for root.  Default: ``":"``.
        set_as_current: If ``True``, set the new namespace as the current active
            namespace after creation.  Default: ``False``.

    Returns:
        ActionResultModel dict with ``namespace``, ``parent``, and ``full_path``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return maya_error("Namespace name cannot be empty", "Provide a valid name")

        previous = cmds.namespaceInfo(currentNamespace=True)
        cmds.namespace(setNamespace=parent)

        if cmds.namespace(exists=name):
            cmds.namespace(setNamespace=previous)
            return maya_error(
                "Namespace already exists: {}".format(name),
                "Use rename_namespace or choose a different name",
            )

        cmds.namespace(add=name)
        full_path = "{}:{}".format(parent.rstrip(":"), name) if parent != ":" else ":{}".format(name)

        if set_as_current:
            cmds.namespace(setNamespace=full_path)
        else:
            cmds.namespace(setNamespace=previous)

        return maya_success(
            "Created namespace '{}'".format(full_path),
            prompt="Use list_namespaces to verify or rename_namespace to adjust the name.",
            namespace=name,
            parent=parent,
            full_path=full_path,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create namespace")

def main(**kwargs):
    return create_namespace(**kwargs)

if __name__ == "__main__":
    import json

    print(json.dumps(create_namespace("char_hero")))
