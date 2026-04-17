"""List all namespaces in the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_namespaces(root_only: bool = False) -> dict:
    """List all namespaces in the current scene.

    Args:
        root_only: If True, return only top-level namespaces directly under
            the root (``":"``).  If False (default), list all namespaces
            recursively.

    Returns:
        ToolResult dict with ``context.namespaces`` — a list of
        namespace strings — and ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if root_only:
            raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=False) or []
        else:
            raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []

        # Filter built-in namespaces
        built_in = {"UI", "shared"}
        namespaces = [ns for ns in raw if ns not in built_in]

        return skill_success(
            "Found {} namespace(s)".format(len(namespaces)),
            namespaces=namespaces,
            count=len(namespaces),
            prompt="Check the result with list_references or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list namespaces")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_namespaces`."""
    return list_namespaces(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
