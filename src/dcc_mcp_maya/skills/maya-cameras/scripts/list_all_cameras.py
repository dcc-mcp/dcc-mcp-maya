"""List all cameras in the scene with basic attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_all_cameras(include_default: bool = True) -> dict:
    """List all cameras in the scene with basic attributes.

    Args:
        include_default: If False, omit Maya's default cameras
            (``persp``, ``top``, ``front``, ``side``).  Default: True.

    Returns:
        ActionResultModel dict with ``context.cameras`` list.
    """
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

        return skill_success(
            "Found {} camera(s)".format(len(results)),
            cameras=results,
            count=len(results),
            prompt="Check the result with list_cameras or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list cameras")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_all_cameras`."""
    return list_all_cameras(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
