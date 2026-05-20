"""Create a cube and return a small standalone scene report."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def create_report_cube(name: str = "standalone_report_cube", size: float = 1.0) -> dict:
    """Create a cube with no UI dependencies."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyCube(width=size, height=size, depth=size, name=name)
        object_name = result[0]
        objects = cmds.ls(type="transform") or []
        return maya_success(
            "Created standalone report cube",
            object_name=object_name,
            transform_count=len(objects),
            transforms=objects[:20],
        )
    except ImportError:
        return maya_error("Maya not available", "Run this skill inside mayapy or Maya.")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create standalone report cube")


@skill_entry
def main(**kwargs) -> dict:
    return create_report_cube(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
