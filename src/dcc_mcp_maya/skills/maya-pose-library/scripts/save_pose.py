"""Save the current transform values of selected objects as a named pose."""
from __future__ import annotations

import json
import os
from typing import Optional

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

# Default pose library directory
_DEFAULT_POSE_DIR = os.path.join(os.path.expanduser("~"), "maya", "poses")


def _get_pose_dir(pose_dir: Optional[str] = None) -> str:
    """Return the resolved pose directory, creating it if needed."""
    directory = pose_dir if pose_dir else _DEFAULT_POSE_DIR
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return directory


def run(params: dict) -> object:
    """Save the current pose for specified objects.

    Captures translate, rotate, and scale values of each object and writes
    them to a JSON file named ``<pose_name>.pose.json`` in the pose directory.

    Args:
        params: Dictionary with keys:
            - pose_name (str): Name for this pose.
            - objects (list[str]): Objects whose transforms to capture.
                                   Defaults to current selection.
            - pose_dir (str): Directory to save poses. Default ~/maya/poses.
            - attributes (list[str]): Additional attributes to capture beyond
                                      translate/rotate/scale. Optional.

    Returns:
        ActionResultModel with pose file path.
    """
    pose_name = params.get("pose_name", "")
    objects = params.get("objects", None)
    pose_dir = params.get("pose_dir", None)
    extra_attrs = params.get("attributes", [])

    if not pose_name:
        return error_result("Invalid parameter", "pose_name must not be empty.")

    try:
        objs = objects if objects else (cmds.ls(selection=True) or [])
        if not objs:
            return error_result("No objects", "No objects specified and nothing is selected.")

        base_attrs = ["translateX", "translateY", "translateZ",
                      "rotateX", "rotateY", "rotateZ",
                      "scaleX", "scaleY", "scaleZ"]
        all_attrs = base_attrs + list(extra_attrs)

        pose_data = {}  # type: Dict[str, Dict[str, float]]
        for obj in objs:
            if not cmds.objExists(obj):
                continue
            obj_data = {}
            for attr in all_attrs:
                full = "{0}.{1}".format(obj, attr)
                if cmds.attributeQuery(attr, node=obj, exists=True):
                    try:
                        obj_data[attr] = cmds.getAttr(full)
                    except Exception:
                        pass
            if obj_data:
                pose_data[obj] = obj_data

        directory = _get_pose_dir(pose_dir)
        pose_file = os.path.join(directory, "{0}.pose.json".format(pose_name))
        with open(pose_file, "w") as fh:
            json.dump({"name": pose_name, "objects": pose_data}, fh, indent=2)

        return success_result(
            "Pose '{0}' saved ({1} objects)".format(pose_name, len(pose_data)),
            prompt="Use apply_pose to restore this pose on any compatible rig.",
            pose_name=pose_name,
            pose_file=pose_file,
            object_count=len(pose_data),
        )
    except Exception as exc:
        return error_result("Failed to save pose", str(exc))
