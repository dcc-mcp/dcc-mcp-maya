"""List all cameras in the scene with basic attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_all_cameras(include_default: bool = True) -> dict:
    """List all cameras in the scene with basic attributes.

    Args:
        include_default: If False, omit Maya's default cameras
            (``persp``, ``top``, ``front``, ``side``).  Default: True.

    Returns:
        ActionResultModel dict with ``context.cameras`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _DEFAULT_CAMERAS = {"persp", "top", "front", "side"}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        shapes = cmds.ls(type="camera") or []
        results = []
        for shape in shapes:
            transform_list = cmds.listRelatives(shape, parent=True) or [shape]
            transform = transform_list[0]
            if not include_default and transform in _DEFAULT_CAMERAS:
                continue
            entry = {"name": transform, "shape": shape}
            for attr in ("focalLength", "renderable"):
                try:
                    entry[attr] = cmds.getAttr("{}.{}".format(shape, attr))
                except Exception:
                    entry[attr] = None
            results.append(entry)

        return success_result(
            "Found {} camera(s)".format(len(results)),
            cameras=results,
            count=len(results),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_all_cameras failed")
        return error_result("Failed to list cameras", str(exc)).to_dict()


def main(**kwargs):
    return list_all_cameras(**kwargs)


if __name__ == "__main__":
    import json

    result = list_all_cameras()
    print(json.dumps(result))
