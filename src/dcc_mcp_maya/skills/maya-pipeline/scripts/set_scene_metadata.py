"""Write pipeline metadata into Maya scene's fileInfo block."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Write pipeline metadata key-value pairs into the Maya scene.

    Uses cmds.fileInfo to embed string metadata that persists inside
    .ma/.mb files, compatible with Shotgrid, Ftrack, and custom pipelines.

    Args:
        params: Dictionary containing:
            - metadata (dict[str, str]): Key-value pairs to write. Required.
                                         Values are coerced to strings.

    Returns:
        ActionResultModel listing written keys.
    """
    metadata_raw = params.get("metadata", {})
    if not isinstance(metadata_raw, dict) or not metadata_raw:
        return error_result(
            "Invalid parameters",
            "'metadata' must be a non-empty dict of key-value pairs.",
        )

    metadata: Dict[str, str] = {str(k): str(v) for k, v in metadata_raw.items()}

    try:
        for key, value in metadata.items():
            cmds.fileInfo(key, value)

        return success_result(
            "Wrote {} metadata key(s)".format(len(metadata)),
            prompt="Use get_scene_metadata to verify the stored values.",
            written_keys=list(metadata.keys()),
        )
    except Exception as exc:
        return error_result("Failed to set scene metadata", str(exc))
