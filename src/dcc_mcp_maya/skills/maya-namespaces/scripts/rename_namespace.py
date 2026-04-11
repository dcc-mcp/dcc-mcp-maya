"""Rename an existing Maya namespace."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
            return skill_error("Namespace name cannot be empty", "Provide a valid name")
        if old_rel in _PROTECTED:
            return skill_error(
                "Cannot rename protected namespace: {}".format(old_rel),
                "UI and shared are Maya built-in namespaces",
            )

        if not cmds.namespace(exists=":{}".format(old_rel)):
            return skill_error(
                "Namespace not found: {}".format(old_name),
                "Verify the namespace with list_namespaces",
            )

        if cmds.namespace(exists=":{}".format(new_rel)):
            return skill_error(
                "Namespace already exists: {}".format(new_name),
                "Choose a different name",
            )

        cmds.namespace(rename=[old_rel, new_rel])

        return skill_success(
            "Renamed namespace '{}' -> '{}'".format(old_rel, new_rel),
            prompt="Use list_namespaces to verify the rename.",
            old_name=old_rel,
            new_name=new_rel,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to rename namespace")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`rename_namespace`."""
    return rename_namespace(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
