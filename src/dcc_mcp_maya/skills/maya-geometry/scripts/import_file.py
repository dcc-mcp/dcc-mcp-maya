"""Import a file into the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import Any, List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_PLUGIN_BY_EXTENSION = {
    ".abc": ("AbcImport",),
    ".fbx": ("fbxmaya",),
    ".obj": ("objExport",),
}


def _normalize_path(path: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded.replace("\\", "/")


def _required_plugins(path: str) -> List[str]:
    return list(_PLUGIN_BY_EXTENSION.get(os.path.splitext(path)[1].lower(), ()))


def _ensure_plugins(cmds: Any, plugin_names: List[str]) -> List[str]:
    loaded = []
    for plugin_name in plugin_names:
        if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
            cmds.loadPlugin(plugin_name)
            loaded.append(plugin_name)
    return loaded


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
        ToolResult dict with ``context.imported_nodes`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not file_path:
            return skill_error("Missing file_path", "file_path is required")
        normalized = _normalize_path(file_path)
        if not os.path.exists(normalized):
            return skill_error("File not found", "{} does not exist on disk".format(normalized), file_path=normalized)

        required_plugins = _required_plugins(normalized)
        try:
            loaded_plugins = _ensure_plugins(cmds, required_plugins)
        except Exception as exc:  # noqa: BLE001
            return skill_error(
                "Import plugin unavailable",
                "Failed to load required plugin for {}: {}".format(normalized, exc),
                file_path=normalized,
                required_plugins=required_plugins,
            )

        kwargs = {"i": True, "prompt": False}  # type: dict
        if namespace:
            kwargs["namespace"] = namespace
        if merge_namespaces:
            kwargs["mergeNamespacesOnClash"] = True

        cmds.file(normalized, **kwargs)
        imported = cmds.ls(importedNodes=True) or []
        return skill_success(
            "Imported {} node(s) from {}".format(len(imported), normalized),
            file_path=normalized,
            imported_nodes=imported,
            count=len(imported),
            required_plugins=required_plugins,
            loaded_plugins=loaded_plugins,
            prompt="Use get_scene_info or list_objects to inspect imported nodes.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to import file: {}".format(file_path))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`import_file`."""
    return import_file(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
