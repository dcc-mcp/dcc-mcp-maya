"""Delete a saved pose from the pose library."""
from __future__ import annotations

import os

from dcc_mcp_core import error_result, success_result

_DEFAULT_POSE_DIR = os.path.join(os.path.expanduser("~"), "maya", "poses")


def run(params: dict) -> object:
    """Delete a .pose.json file from the pose library.

    Args:
        params: Dictionary with keys:
            - pose_name (str): Name of the pose to delete.
            - pose_dir (str): Directory containing the pose. Default ~/maya/poses.

    Returns:
        ActionResultModel confirming deletion.
    """
    pose_name = params.get("pose_name", "")
    pose_dir = params.get("pose_dir", None)

    if not pose_name:
        return error_result("Invalid parameter", "pose_name must not be empty.")

    try:
        directory = pose_dir if pose_dir else _DEFAULT_POSE_DIR
        pose_file = os.path.join(directory, "{0}.pose.json".format(pose_name))

        if not os.path.isfile(pose_file):
            return error_result(
                "Pose not found: '{0}'".format(pose_name),
                "Expected file: {0}".format(pose_file),
            )

        os.remove(pose_file)

        return success_result(
            "Deleted pose '{0}'".format(pose_name),
            prompt="Pose removed. Use list_poses to see remaining poses in the library.",
            pose_name=pose_name,
            deleted_file=pose_file,
        )
    except Exception as exc:
        return error_result("Failed to delete pose", str(exc))
