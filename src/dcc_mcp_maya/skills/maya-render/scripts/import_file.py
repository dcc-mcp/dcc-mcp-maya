"""Import a file into the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def import_file(
    file_path: str,
    namespace: Optional[str] = None,
    merge_namespaces: bool = False,
) -> dict:
    """Import a file into the current Maya scene.

    Supports any format Maya recognises (FBX, OBJ, Alembic, Maya ASCII/Binary,
    etc.).

    Args:
        file_path: Absolute path to the file to import.
        namespace: Optional namespace to assign to imported nodes.
        merge_namespaces: If True, merge with existing namespaces.

    Returns:
        ActionResultModel dict with ``context.imported_nodes`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"i": True}  # type: dict
        if namespace:
            kwargs["namespace"] = namespace
        if merge_namespaces:
            kwargs["mergeNamespacesOnClash"] = True

        cmds.file(file_path, **kwargs)
        imported = cmds.ls(importedNodes=True) or []
        return maya_success(
            "Imported {} node(s) from {}".format(len(imported), file_path),
            file_path=file_path,
            imported_nodes=imported,
            count=len(imported),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to import file: {}".format(file_path))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`import_file`."""
    return import_file(**kwargs)

if __name__ == "__main__":
    import json

    result = import_file()
    print(json.dumps(result))
