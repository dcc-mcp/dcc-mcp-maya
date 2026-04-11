"""Import a motion capture file (BVH or FBX) into the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def import_mocap(
    file_path: str,
    namespace: str = "mocap",
    merge_mode: str = "add",
) -> dict:
    """Import mocap file and return root joint names.

    Args:
        file_path: Absolute path to a BVH or FBX mocap file.
        namespace: Namespace prefix for imported nodes. Default ``"mocap"``.
        merge_mode: FBX merge mode: ``"add"``, ``"merge"``, or ``"exmerge"``. Default ``"add"``.

    Returns:
        ActionResultModel dict with ``context.root_joints`` and ``context.joint_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not file_path:
        return error_result("Missing parameter", "'file_path' is required").to_dict()

    if not os.path.isfile(file_path):
        return error_result(
            "File not found: {}".format(file_path),
            "Verify the file path and ensure the file exists.",
        ).to_dict()

    ext = os.path.splitext(file_path)[1].lower()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        before = set(cmds.ls(type="joint") or [])

        if ext == ".bvh":
            cmds.file(
                file_path,
                i=True,
                type="BVH",
                ignoreVersion=True,
                mergeNamespacesOnClash=False,
                namespace=namespace,
                options="mo=1",
            )
        elif ext in (".fbx", ".mb", ".ma"):
            cmds.loadPlugin("fbxmaya", quiet=True)
            cmds.file(
                file_path,
                i=True,
                type="FBX",
                ignoreVersion=True,
                mergeNamespacesOnClash=False,
                namespace=namespace,
                options="fbx" + merge_mode,
            )
        else:
            return error_result(
                "Unsupported file type: {}".format(ext),
                "Supported formats: .bvh, .fbx. Convert your file first.",
            ).to_dict()

        after = set(cmds.ls(type="joint") or [])
        new_joints = sorted(after - before)
        roots = [j for j in new_joints if not cmds.listRelatives(j, parent=True, type="joint")]

        return success_result(
            "Imported mocap from '{}' ({} joints)".format(
                os.path.basename(file_path), len(new_joints)
            ),
            prompt="Mocap skeleton imported. Use create_hik_definition to set up retargeting.",
            file=file_path,
            namespace=namespace,
            joint_count=len(new_joints),
            root_joints=roots,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("import_mocap failed")
        return error_result("Failed to import mocap file", str(exc)).to_dict()


def main(**kwargs):
    return import_mocap(**kwargs)


if __name__ == "__main__":
    import json
    import sys
    result = import_mocap(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(result))
