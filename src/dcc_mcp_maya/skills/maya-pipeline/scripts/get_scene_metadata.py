"""Read pipeline metadata stored in Maya scene's fileInfo or root node attributes."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Read pipeline metadata from the Maya scene.

    Reads metadata stored via cmds.fileInfo (key-value pairs embedded in the
    .ma/.mb file) as well as any custom string attributes on the scene root.

    Args:
        params: Dictionary containing:
            - keys (list[str]): Optional list of specific metadata keys to retrieve.
                                If omitted, all fileInfo entries are returned.

    Returns:
        ActionResultModel with metadata dict.
    """
    keys: List[str] = list(params.get("keys", []))  # type: ignore[arg-type]

    try:
        # fileInfo returns flat list: [key, value, key, value, ...]
        raw: List[str] = cmds.fileInfo(query=True) or []
        all_meta: Dict[str, str] = {}
        for i in range(0, len(raw) - 1, 2):
            all_meta[raw[i]] = raw[i + 1]

        if keys:
            filtered = {k: all_meta[k] for k in keys if k in all_meta}
        else:
            filtered = all_meta

        return success_result(
            "Retrieved {} metadata key(s)".format(len(filtered)),
            prompt="Use set_scene_metadata to add or update pipeline metadata.",
            metadata=filtered,
            count=len(filtered),
        )
    except Exception as exc:
        return error_result("Failed to get scene metadata", str(exc))
