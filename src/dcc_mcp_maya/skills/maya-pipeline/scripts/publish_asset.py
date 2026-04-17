"""Export selected geometry to a versioned publish path (FBX or MA)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
import re
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _next_version(publish_dir: str, asset_name: str, fmt: str) -> int:
    """Scan existing publish files and return the next version number."""
    pattern = re.compile(r"^{}_v(\d+)\.{}$".format(re.escape(asset_name), re.escape(fmt)))
    max_ver = 0
    if os.path.isdir(publish_dir):
        for entry in os.listdir(publish_dir):
            m = pattern.match(entry)
            if m:
                max_ver = max(max_ver, int(m.group(1)))
    return max_ver + 1


def publish_asset(
    asset_name: str,
    publish_dir: str,
    format: str = "fbx",
    frame_range: Optional[List[int]] = None,
    version: Optional[int] = None,
) -> dict:
    """Publish the current selection as a versioned asset.

    Args:
        asset_name: Base name for the published file.
        publish_dir: Directory to publish into.
        format: ``"fbx"`` | ``"ma"``. Default ``"fbx"``.
        frame_range: ``[start, end]`` for FBX animation export. Default: current frame only.
        version: Explicit version number; if omitted, auto-increments.

    Returns:
        ToolResult dict with ``context.publish_path`` and ``context.version``.
    """

    if not asset_name:
        return skill_error("No asset_name provided", "Provide 'asset_name' parameter.")
    if not publish_dir:
        return skill_error("No publish_dir provided", "Provide 'publish_dir' parameter.")

    fmt = format.lower()

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        selection = cmds.ls(selection=True)
        if not selection:
            return skill_error("Nothing selected", "Select at least one object before publishing.")

        if not os.path.isdir(publish_dir):
            os.makedirs(publish_dir)

        ver = version if version is not None else _next_version(publish_dir, asset_name, fmt)
        filename = "{}_v{:03d}.{}".format(asset_name, ver, fmt)
        publish_path = os.path.join(publish_dir, filename).replace("\\", "/")

        if fmt == "fbx":
            mel.eval("FBXExportSmoothingGroups -v true")
            if frame_range and len(frame_range) == 2:
                mel.eval("FBXExportBakeAnimation -v true")
                mel.eval("FBXExportBakeAnimationStart -v {}".format(int(frame_range[0])))
                mel.eval("FBXExportBakeAnimationEnd -v {}".format(int(frame_range[1])))
            mel.eval('FBXExport -f "{}" -s'.format(publish_path))

        elif fmt == "ma":
            cmds.file(
                publish_path,
                exportSelected=True,
                type="mayaAscii",
                force=True,
            )
        else:
            return skill_error("Unsupported format '{}'".format(fmt), "Use 'fbx' or 'ma'.")

        return skill_success(
            "Published {} v{:03d} to {}".format(asset_name, ver, publish_path),
            prompt="Asset published. Tag it with tag_asset_metadata for pipeline tracking.",
            publish_path=publish_path,
            version=ver,
            asset_name=asset_name,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Publish failed")


@skill_entry
def main(**kwargs):
    return publish_asset(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
