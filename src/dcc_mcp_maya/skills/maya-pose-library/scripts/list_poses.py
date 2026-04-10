"""List all saved poses in the pose library directory."""
from __future__ import annotations

import json
import os

from dcc_mcp_core import error_result, success_result

_DEFAULT_POSE_DIR = os.path.join(os.path.expanduser("~"), "maya", "poses")


def run(params: dict) -> object:
    """List all .pose.json files in the pose library directory.

    Args:
        params: Dictionary with keys:
            - pose_dir (str): Directory to list. Default ~/maya/poses.

    Returns:
        ActionResultModel with list of pose metadata.
    """
    pose_dir = params.get("pose_dir", None)

    try:
        directory = pose_dir if pose_dir else _DEFAULT_POSE_DIR
        if not os.path.isdir(directory):
            return success_result(
                "Pose library directory does not exist yet",
                prompt="Use save_pose to create your first pose.",
                poses=[],
                count=0,
                directory=directory,
            )

        pose_files = [f for f in os.listdir(directory) if f.endswith(".pose.json")]
        poses = []  # type: List[dict]
        for fname in sorted(pose_files):
            fpath = os.path.join(directory, fname)
            try:
                with open(fpath, "r") as fh:
                    data = json.load(fh)
                obj_count = len(data.get("objects", {}))
            except Exception:
                obj_count = -1
            pose_name = fname.replace(".pose.json", "")
            poses.append({"name": pose_name, "file": fpath, "object_count": obj_count})

        return success_result(
            "Found {0} pose(s) in '{1}'".format(len(poses), directory),
            prompt="Use apply_pose to restore a pose, or save_pose to add a new one.",
            poses=poses,
            count=len(poses),
            directory=directory,
        )
    except Exception as exc:
        return error_result("Failed to list poses", str(exc))
