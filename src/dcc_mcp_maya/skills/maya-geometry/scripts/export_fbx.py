"""Export the current Maya scene to FBX."""

# Import future modules
from __future__ import annotations

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _ensure_plugin(cmds, plugin_name: str) -> None:
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def export_fbx(path: str, selected_only: bool = False) -> dict:
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not path:
            return skill_error("Missing path", "path is required")
        _ensure_plugin(cmds, "fbxmaya")
        if selected_only:
            exported_path = cmds.file(path, force=True, options="v=0;", type="FBX export", exportSelected=True)
        else:
            exported_path = cmds.file(path, force=True, options="v=0;", type="FBX export", exportAll=True)
        return skill_success("Exported FBX", path=exported_path or path, selected_only=selected_only)
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to export FBX")


@skill_entry
def main(**kwargs) -> dict:
    return export_fbx(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
