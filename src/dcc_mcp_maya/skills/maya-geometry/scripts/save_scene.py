"""Save the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_VALID_FILE_TYPES = {"mayaAscii", "mayaBinary"}


def save_scene(path: str, file_type: str = "mayaAscii") -> dict:
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not path:
            return skill_error("Missing path", "path is required")
        if file_type not in _VALID_FILE_TYPES:
            return skill_error("Invalid file_type", "file_type must be mayaAscii or mayaBinary")
        cmds.file(rename=path)
        saved_path = cmds.file(save=True, type=file_type)
        return skill_success("Saved scene", path=saved_path or path, file_type=file_type)
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to save scene")


@skill_entry
def main(**kwargs) -> dict:
    return save_scene(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
