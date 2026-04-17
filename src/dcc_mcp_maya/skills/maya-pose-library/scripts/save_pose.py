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


# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success  # noqa: E402


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
        ToolResult dict with ``context.file_path`` and
        ``context.control_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nodes = controls if controls else (cmds.ls(selection=True) or [])
        if not nodes:
            return skill_error(
                "No controls specified",
                "Provide 'controls' or select nodes in Maya",
            )

        attrs = attributes if attributes else _POSE_ATTRS

        if not overwrite and os.path.exists(file_path):
            return skill_error(
                "File already exists: {}".format(file_path),
                "Set overwrite=True to replace the existing pose file",
            )

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

        return skill_success(
            "Saved pose for {} control(s) to '{}'".format(len(pose_data), file_path),
            prompt="Use load_pose to apply this pose back to the rig.",
            file_path=file_path,
            control_count=len(pose_data),
            controls=list(pose_data.keys()),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to save pose to '{}'".format(file_path))


@skill_entry
def main(**kwargs):
    return save_pose(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
