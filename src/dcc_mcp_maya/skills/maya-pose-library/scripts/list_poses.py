"""List all saved pose files in a directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def list_poses(
    directory: str,
    recursive: bool = False,
) -> dict:
    """List all saved pose JSON files in a directory.

    Args:
        directory: Path to the directory containing ``.json`` pose files.
        recursive: If True, search subdirectories recursively.
            Default: False.

    Returns:
        ActionResultModel dict with ``context.poses`` (list of dicts with
        ``file``, ``control_count``) and ``context.count``.
    """

    try:
        if not os.path.isdir(directory):
            return maya_error(
                "Directory not found: {}".format(directory),
                "'{}'  does not exist on disk".format(directory),
            )

        pose_files = []

        if recursive:
            for root, _dirs, files in os.walk(directory):
                for fname in files:
                    if fname.lower().endswith(".json"):
                        pose_files.append(os.path.join(root, fname))
        else:
            for fname in os.listdir(directory):
                if fname.lower().endswith(".json"):
                    pose_files.append(os.path.join(directory, fname))

        pose_files.sort()

        poses = []
        for fpath in pose_files:
            info = {"file": fpath, "control_count": 0}  # type: dict
            try:
                with open(fpath, "r") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    info["control_count"] = len(data)
                    info["controls"] = list(data.keys())
            except Exception:
                info["parse_error"] = True
            poses.append(info)

        return maya_success(
            "Found {} pose file(s) in '{}'".format(len(poses), directory),
            prompt="Use load_pose with one of the listed file paths to apply a pose.",
            poses=poses,
            count=len(poses),
            directory=directory,
        )
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list poses in '{}'".format(directory))


def main(**kwargs):
    return list_poses(**kwargs)


if __name__ == "__main__":
    import json as _json

    result = list_poses("/tmp/poses")
    print(_json.dumps(result))
