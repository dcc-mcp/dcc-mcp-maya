"""Apply a saved pose JSON file to matching controls in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging

logger = logging.getLogger(__name__)


# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success  # noqa: E402


def load_pose(
    file_path: str,
    namespace: str = "",
    skip_missing: bool = True,
) -> dict:
    """Apply a saved pose JSON file to matching controls in the scene.

    Args:
        file_path: Absolute path to the ``.json`` pose file.
        namespace: Optional Maya namespace prefix to prepend to node names
            (e.g. ``"char_ref:"``).
        skip_missing: If True, silently skip controls not found in the scene.
            If False, return an error when any control is missing.
            Default: True.

    Returns:
        ActionResultModel dict with ``context.applied_count`` and
        ``context.missing_controls``.
    """

    try:
        import os

        import maya.cmds as cmds  # noqa: PLC0415

        if not os.path.isfile(file_path):
            return skill_error(
                "Pose file not found: {}".format(file_path),
                "'{}'  does not exist on disk".format(file_path),
            )

        with open(file_path, "r") as fh:
            pose_data = json.load(fh)

        applied = 0
        missing = []

        for node_name, attrs in pose_data.items():
            full_node = "{}{}".format(namespace, node_name)
            if not cmds.objExists(full_node):
                if skip_missing:
                    missing.append(full_node)
                    continue
                return skill_error(
                    "Control not found: {}".format(full_node),
                    "Use skip_missing=True to ignore missing nodes",
                )

            for attr, value in attrs.items():
                full_attr = "{}.{}".format(full_node, attr)
                try:
                    if cmds.attributeQuery(attr, node=full_node, exists=True):
                        if not cmds.getAttr(full_attr, lock=True):
                            cmds.setAttr(full_attr, value)
                except Exception as exc:
                    logger.warning("Could not set %s: %s", full_attr, exc)

            applied += 1

        return skill_success(
            "Applied pose to {}/{} control(s)".format(applied, len(pose_data)),
            prompt="Use save_pose to capture any modifications as a new pose.",
            applied_count=applied,
            total_controls=len(pose_data),
            missing_controls=missing,
            file_path=file_path,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to load pose from '{}'".format(file_path))


@skill_entry
def main(**kwargs):
    return load_pose(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
