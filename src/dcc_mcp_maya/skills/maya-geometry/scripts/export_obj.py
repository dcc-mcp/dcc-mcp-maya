"""Export the current Maya scene to OBJ."""

# Import future modules
from __future__ import annotations

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _ensure_plugin(cmds, plugin_name: str) -> None:
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def export_obj(path: str) -> dict:
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not path:
            return skill_error("Missing path", "path is required")
        _ensure_plugin(cmds, "objExport")
        exported_path = cmds.file(
            path,
            force=True,
            options="groups=1;ptgroups=1;materials=1;smoothing=1;normals=1",
            type="OBJexport",
            exportAll=True,
        )
        return skill_success("Exported OBJ", path=exported_path or path)
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to export OBJ")


@skill_entry
def main(**kwargs) -> dict:
    return export_obj(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
