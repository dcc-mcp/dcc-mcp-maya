"""Rename an existing Maya namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def rename_namespace(
    old_name: str,
    new_name: str,
) -> dict:
    """Rename a namespace.

    All objects within the namespace retain their membership; only the namespace
    identifier changes.

    Args:
        old_name: Current namespace name (relative, without leading ``:``)
            or full path (e.g. ``":char_hero"``).
        new_name: Target namespace name (relative).

    Returns:
        ActionResultModel dict with ``old_name``, ``new_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        old_rel = old_name.lstrip(":")
        new_rel = new_name.lstrip(":")

        _PROTECTED = {"UI", "shared"}
        if not old_rel:
            return maya_error("Namespace name cannot be empty", "Provide a valid name")
        if old_rel in _PROTECTED:
            return maya_error(
                "Cannot rename protected namespace: {}".format(old_rel),
                "UI and shared are Maya built-in namespaces",
            )

        if not cmds.namespace(exists=":{}".format(old_rel)):
            return maya_error(
                "Namespace not found: {}".format(old_name),
                "Verify the namespace with list_namespaces",
            )

        if cmds.namespace(exists=":{}".format(new_rel)):
            return maya_error(
                "Namespace already exists: {}".format(new_name),
                "Choose a different name",
            )

        cmds.namespace(rename=[old_rel, new_rel])

        return maya_success(
            "Renamed namespace '{}' -> '{}'".format(old_rel, new_rel),
            prompt="Use list_namespaces to verify the rename.",
            old_name=old_rel,
            new_name=new_rel,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to rename namespace")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`rename_namespace`."""
    return rename_namespace(**kwargs)

if __name__ == "__main__":
    import json

    print(json.dumps(rename_namespace("char_hero", "char_hero_v2")))
