"""Create a Maya polygon sphere."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_sphere(radius: float = 1.0, name: Optional[str] = None) -> dict:
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if radius <= 0:
            return skill_error("Invalid radius", "radius must be greater than 0")
        kwargs = {"radius": radius}
        if name:
            kwargs["name"] = name
        result = cmds.polySphere(**kwargs)
        transform = result[0] if result else name
        return skill_success("Created sphere '{}'".format(transform), object_name=transform, radius=radius)
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create sphere")


@skill_entry
def main(**kwargs) -> dict:
    return create_sphere(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
