"""List all non-default namespaces with object counts."""

# Import future modules
from __future__ import annotations

# Import built-in modules

_DEFAULT_NAMESPACES = {"UI", "shared"}


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def list_namespaces(include_defaults: bool = False) -> dict:
    """List all namespaces in the current scene.

    Args:
        include_defaults: If ``True``, include the built-in ``UI`` and ``shared``
            namespaces.  Default: ``False``.

    Returns:
        ActionResultModel dict with ``namespaces`` list.  Each entry contains
        ``name``, ``full_path``, and ``object_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        namespaces = []
        for ns in raw:
            base = ns.split(":")[-1]
            if not include_defaults and base in _DEFAULT_NAMESPACES:
                continue
            full_path = ns if ns.startswith(":") else ":{}".format(ns)
            # Count objects in namespace
            try:
                objects = cmds.ls("{}:*".format(ns.lstrip(":"))) or []
                obj_count = len(objects)
            except Exception:
                obj_count = 0

            namespaces.append(
                {
                    "name": base,
                    "full_path": full_path,
                    "object_count": obj_count,
                }
            )

        return maya_success(
            "Found {} namespace(s)".format(len(namespaces)),
            prompt="Use rename_namespace or remove_namespace to manage them.",
            namespaces=namespaces,
            count=len(namespaces),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list namespaces")

def main(**kwargs):
    return list_namespaces(**kwargs)

if __name__ == "__main__":
    import json

    print(json.dumps(list_namespaces()))
