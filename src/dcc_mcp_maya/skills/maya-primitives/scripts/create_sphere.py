"""Create a polygon sphere."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def create_sphere(radius: float = 1.0, name: Optional[str] = None) -> dict:
    """Create a polygon sphere.

    Args:
        radius: Sphere radius. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polySphere(radius=radius, subdivisionsAxis=20, subdivisionsHeight=20)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return maya_success(f"Created sphere: {obj}", object_name=obj, radius=radius)
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create sphere")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_sphere`."""
    return create_sphere(**kwargs)


if __name__ == "__main__":
    import json

    result = create_sphere()
    print(json.dumps(result))
