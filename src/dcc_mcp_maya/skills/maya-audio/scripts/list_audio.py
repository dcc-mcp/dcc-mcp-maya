"""List all sound nodes in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_audio() -> dict:
    """List all sound nodes in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.sound_nodes`` (list of dicts
        with ``node``, ``file_path``, ``offset``) and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        sound_nodes = cmds.ls(type="audio") or []
        result = []
        for node in sound_nodes:
            file_path = cmds.getAttr("{}.filename".format(node)) or ""
            offset = cmds.getAttr("{}.offset".format(node)) or 0.0
            result.append(
                {
                    "node": node,
                    "file_path": file_path,
                    "offset": offset,
                }
            )

        return skill_success(
            "Found {} sound node(s)".format(len(result)),
            prompt="Use set_timeline_audio to activate a sound, or remove_audio to delete one.",
            sound_nodes=result,
            count=len(result),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list audio nodes")


@skill_entry
def main(**kwargs):
    return list_audio(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
