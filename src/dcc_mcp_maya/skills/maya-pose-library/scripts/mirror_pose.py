"""Mirror a pose left/right by flipping axis-specific translate/rotate values."""
from __future__ import annotations

import json
import os

from dcc_mcp_core import error_result, success_result

_DEFAULT_POSE_DIR = os.path.join(os.path.expanduser("~"), "maya", "poses")

# Attributes to negate when mirroring across YZ plane (left ↔ right)
_MIRROR_YZ_NEGATE = {"translateX", "rotateY", "rotateZ"}
# For XZ plane (front ↔ back)
_MIRROR_XZ_NEGATE = {"translateZ", "rotateX", "rotateY"}


def run(params: dict) -> object:
    """Mirror a pose and save it as a new pose.

    Flips axis-dependent translate/rotate values according to the chosen
    mirror plane.  Left/right name swapping uses configurable prefixes.

    Args:
        params: Dictionary with keys:
            - pose_name (str): Source pose to mirror.
            - mirrored_pose_name (str): Name for the mirrored pose.
            - mirror_axis (str): "YZ" (default, left↔right) or "XZ" (front↔back).
            - left_prefix (str): Prefix identifying left-side objects. Default "L_".
            - right_prefix (str): Prefix identifying right-side objects. Default "R_".
            - pose_dir (str): Pose library directory. Default ~/maya/poses.

    Returns:
        ActionResultModel with new pose file path.
    """
    pose_name = params.get("pose_name", "")
    mirrored_name = params.get("mirrored_pose_name", "")
    mirror_axis = params.get("mirror_axis", "YZ").upper()
    left_prefix = params.get("left_prefix", "L_")
    right_prefix = params.get("right_prefix", "R_")
    pose_dir = params.get("pose_dir", None)

    if not pose_name:
        return error_result("Invalid parameter", "pose_name must not be empty.")
    if not mirrored_name:
        return error_result("Invalid parameter", "mirrored_pose_name must not be empty.")
    if mirror_axis not in ("YZ", "XZ"):
        return error_result("Invalid mirror_axis", "Use 'YZ' or 'XZ'.")

    try:
        directory = pose_dir if pose_dir else _DEFAULT_POSE_DIR
        src_file = os.path.join(directory, "{0}.pose.json".format(pose_name))
        if not os.path.isfile(src_file):
            return error_result(
                "Pose not found: '{0}'".format(pose_name),
                "Expected file: {0}".format(src_file),
            )

        with open(src_file, "r") as fh:
            src_data = json.load(fh)

        negate_set = _MIRROR_YZ_NEGATE if mirror_axis == "YZ" else _MIRROR_XZ_NEGATE
        objects_data = src_data.get("objects", {})
        mirrored_objects = {}

        for obj_name, attrs in objects_data.items():
            # Swap left/right prefixes in object name
            if obj_name.startswith(left_prefix):
                mirrored_obj = right_prefix + obj_name[len(left_prefix):]
            elif obj_name.startswith(right_prefix):
                mirrored_obj = left_prefix + obj_name[len(right_prefix):]
            else:
                mirrored_obj = obj_name

            mirrored_attrs = {}
            for attr, value in attrs.items():
                if attr in negate_set:
                    mirrored_attrs[attr] = -float(value)
                else:
                    mirrored_attrs[attr] = value
            mirrored_objects[mirrored_obj] = mirrored_attrs

        out_file = os.path.join(directory, "{0}.pose.json".format(mirrored_name))
        with open(out_file, "w") as fh:
            json.dump({"name": mirrored_name, "objects": mirrored_objects}, fh, indent=2)

        return success_result(
            "Mirrored pose '{0}' → '{1}' ({2} axis)".format(pose_name, mirrored_name, mirror_axis),
            prompt="Mirror complete. Use apply_pose to apply the mirrored pose.",
            mirrored_pose_name=mirrored_name,
            pose_file=out_file,
            object_count=len(mirrored_objects),
        )
    except Exception as exc:
        return error_result("Failed to mirror pose", str(exc))
