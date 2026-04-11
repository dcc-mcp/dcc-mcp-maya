"""Remove a namespace and merge its contents into the parent namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def remove_namespace(
    name: str,
    force: bool = False,
) -> dict:
    """Remove a namespace, merging its objects into the parent.

    When ``force`` is ``True`` the namespace is removed even if it contains
    objects (they are reparented to the parent namespace).  When ``False``,
    an error is returned if the namespace is not empty.

    Args:
        name: Namespace to remove (relative or full path).
        force: Move objects to parent namespace before removal.  Default: ``False``.

    Returns:
        ActionResultModel dict with ``namespace`` and ``merged_objects``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        rel = name.lstrip(":")
        if not cmds.namespace(exists=rel):
            return maya_error(
                "Namespace not found: {}".format(name),
                "Verify the namespace with list_namespaces",
            )

        objects_in_ns = cmds.ls("{}:*".format(rel)) or []

        if objects_in_ns and not force:
            return maya_error(
                "Namespace '{}' is not empty ({} objects)".format(rel, len(objects_in_ns)),
                "Set force=True to merge objects into the parent namespace",
            )

        if objects_in_ns and force:
            cmds.namespace(moveNamespace=[rel, ":"], force=True)

        cmds.namespace(removeNamespace=rel)

        return maya_success(
            "Removed namespace '{}' ({} objects merged)".format(rel, len(objects_in_ns)),
            prompt="Use list_namespaces to confirm removal.",
            namespace=rel,
            merged_objects=len(objects_in_ns),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to remove namespace")


def main(**kwargs):
    return remove_namespace(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(remove_namespace("char_hero", force=True)))
