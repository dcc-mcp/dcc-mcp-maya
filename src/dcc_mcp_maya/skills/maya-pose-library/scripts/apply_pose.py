"""Apply a saved pose to matching objects in the scene."""
from __future__ import annotations

import json
import os

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

_DEFAULT_POSE_DIR = os.path.join(os.path.expanduser("~"), "maya", "poses")


def run(params: dict) -> object:
    """Apply a saved pose to scene objects.

    Reads a ``.pose.json`` file and sets attribute values on matching objects.
    Non-existent objects are silently skipped.

    Args:
        params: Dictionary with keys:
            - pose_name (str): Name of the pose to apply.
            - pose_dir (str): Directory containing pose files. Default ~/maya/poses.
            - namespace (str): Optional namespace prefix to prepend to object names.
            - blend (float): Blend factor [0, 1] — 0 keeps current, 1 = full pose. Default 1.0.

    Returns:
        ActionResultModel with applied object count.
    """
    pose_name = params.get("pose_name", "")
    pose_dir = params.get("pose_dir", None)
    namespace = params.get("namespace", "")
    blend = float(params.get("blend", 1.0))

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

        with open(pose_file, "r") as fh:
            pose_data = json.load(fh)

        objects_data = pose_data.get("objects", {})
        applied = 0
        for obj_name, attrs in objects_data.items():
            target = "{0}:{1}".format(namespace, obj_name) if namespace else obj_name
            if not cmds.objExists(target):
                continue
            for attr, value in attrs.items():
                full = "{0}.{1}".format(target, attr)
                if not cmds.attributeQuery(attr, node=target, exists=True):
                    continue
                try:
                    if blend < 1.0:
                        current = cmds.getAttr(full)
                        value = current + (value - current) * blend
                    cmds.setAttr(full, value)
                except Exception:
                    pass
            applied += 1

        return success_result(
            "Applied pose '{0}' to {1} objects".format(pose_name, applied),
            prompt="Pose applied. Use save_pose to save modifications as a new pose.",
            pose_name=pose_name,
            applied_count=applied,
            blend=blend,
        )
    except Exception as exc:
        return error_result("Failed to apply pose", str(exc))
