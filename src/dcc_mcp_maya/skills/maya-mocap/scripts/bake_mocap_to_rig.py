"""Bake HumanIK retargeted motion onto a rig skeleton."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def bake_mocap_to_rig(
    source_character: str,
    target_character: str,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    bake_step: float = 1.0,
) -> dict:
    """Retarget and bake mocap motion from source HIK character onto target rig.

    Args:
        source_character: HIK character name of the mocap source.
        target_character: HIK character name of the target rig.
        start_frame: Start frame for baking. Defaults to playback start.
        end_frame: End frame for baking. Defaults to playback end.
        bake_step: Frame step for baking. Default ``1.0``.

    Returns:
        ToolResult dict confirming bake completion.
    """

    if not source_character or not target_character:
        return skill_error(
            "Missing parameters",
            "'source_character' and 'target_character' are required",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if start_frame is None:
            start_frame = int(cmds.playbackOptions(query=True, minTime=True))
        if end_frame is None:
            end_frame = int(cmds.playbackOptions(query=True, maxTime=True))

        cmds.loadPlugin("mayaHIK", quiet=True)
        mel.eval('hikSetCharacterInput("{}", "{}")'.format(target_character, source_character))
        mel.eval("hikUpdateCurrentCharacterFromUI")

        target_joints = cmds.ls(type="joint") or []
        if not target_joints:
            return skill_error(
                "No joints found in scene to bake onto",
                "Ensure the target rig skeleton is present in the scene.",
            )

        cmds.bakeResults(
            target_joints,
            time=(start_frame, end_frame),
            sampleBy=bake_step,
            attribute=["tx", "ty", "tz", "rx", "ry", "rz"],
            simulation=True,
            disableImplicitControl=True,
            preserveOutsideKeys=False,
            sparseAnimCurveBake=False,
        )

        return skill_success(
            "Baked motion from '{}' onto '{}' ({}-{})".format(
                source_character, target_character, start_frame, end_frame
            ),
            prompt="Motion baked. Use clean_mocap_keys to reduce keyframe density.",
            source=source_character,
            target=target_character,
            start_frame=start_frame,
            end_frame=end_frame,
            baked_joints=len(target_joints),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake mocap motion")


@skill_entry
def main(**kwargs):
    return bake_mocap_to_rig(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
