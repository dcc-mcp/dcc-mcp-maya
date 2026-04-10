"""Save current attribute values of selected controls to a JSON pose file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

_POSE_ATTRS = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]


def save_pose(
    file_path: str,
    controls: Optional[List[str]] = None,
    attributes: Optional[List[str]] = None,
    overwrite: bool = True,
) -> dict:
    """Save current attribute values of controls to a JSON pose file.

    Args:
        file_path: Absolute path for the output ``.json`` pose file.
        controls: List of control node names to capture.  If None, the
            current Maya selection is used.
        attributes: List of attribute names to capture per control.
            Defaults to ``tx ty tz rx ry rz sx sy sz``.
        overwrite: If False and the file exists, return an error instead
            of overwriting.  Default: True.

    Returns:
        ActionResultModel dict with ``context.file_path`` and
        ``context.control_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nodes = controls if controls else (cmds.ls(selection=True) or [])
        if not nodes:
            return error_result(
                "No controls specified",
                "Provide 'controls' or select nodes in Maya",
            ).to_dict()

        attrs = attributes if attributes else _POSE_ATTRS

        if not overwrite and os.path.exists(file_path):
            return error_result(
                "File already exists: {}".format(file_path),
                "Set overwrite=True to replace the existing pose file",
            ).to_dict()

        pose_data = {}  # type: dict
        for node in nodes:
            if not cmds.objExists(node):
                logger.warning("Control not found, skipping: %s", node)
                continue
            node_data = {}
            for attr in attrs:
                full = "{}.{}".format(node, attr)
                if cmds.attributeQuery(attr, node=node, exists=True):
                    try:
                        node_data[attr] = cmds.getAttr(full)
                    except Exception:
                        pass
            pose_data[node] = node_data

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w") as fh:
            json.dump(pose_data, fh, indent=2)

        return success_result(
            "Saved pose for {} control(s) to '{}'".format(len(pose_data), file_path),
            prompt="Use load_pose to apply this pose back to the rig.",
            file_path=file_path,
            control_count=len(pose_data),
            controls=list(pose_data.keys()),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("save_pose failed")
        return error_result("Failed to save pose to '{}'".format(file_path), str(exc)).to_dict()


def main(**kwargs):
    return save_pose(**kwargs)


if __name__ == "__main__":
    import json as _json

    result = save_pose("/tmp/my_pose.json")
    print(_json.dumps(result))
