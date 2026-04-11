"""List all namespaces in the current scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_namespaces(root_only: bool = False) -> dict:
    """List all namespaces in the current scene.

    Args:
        root_only: If True, return only top-level namespaces directly under
            the root (``":"``).  If False (default), list all namespaces
            recursively.

    Returns:
        ActionResultModel dict with ``context.namespaces`` — a list of
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

        return maya_success(
            "Found {} namespace(s)".format(len(namespaces)),
            namespaces=namespaces,
            count=len(namespaces),
            prompt="Check the result with list_references or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list namespaces")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_namespaces`."""
    return list_namespaces(**kwargs)


if __name__ == "__main__":
    import json

    result = list_namespaces()
    print(json.dumps(result))
