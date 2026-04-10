"""Connect a dynamic field (gravity, turbulence, etc.) to nParticles."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_FIELD_TYPES = {
    "gravity": "gravity",
    "turbulence": "turbulence",
    "drag": "drag",
    "newton": "newton",
    "uniform": "uniform",
    "vortex": "vortex",
    "radial": "radial",
    "air": "air",
}


def add_field_to_nparticles(
    particle_shapes: Optional[List[str]] = None,
    field_type: str = "gravity",
    magnitude: float = 9.8,
    field_name: Optional[str] = None,
) -> dict:
    """Create a dynamic field and connect it to nParticle systems.

    Args:
        particle_shapes: List of ``nParticle`` shape node names.  If None,
            all ``nParticle`` nodes in the scene are targeted.
        field_type: Field type to create — ``"gravity"``, ``"turbulence"``,
            ``"drag"``, ``"newton"``, ``"uniform"``, ``"vortex"``,
            ``"radial"``, ``"air"``.  Default: ``"gravity"``.
        magnitude: Field magnitude (e.g. 9.8 for gravity).  Default: 9.8.
        field_name: Optional name for the created field node.

    Returns:
        ActionResultModel dict with the field node name and connected particles.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ft = field_type.lower()
        if ft not in _FIELD_TYPES:
            return error_result(
                "Unknown field type '{}'".format(field_type),
                "Valid types: {}".format(", ".join(sorted(_FIELD_TYPES))),
            ).to_dict()

        targets = particle_shapes or (cmds.ls(type="nParticle") or [])
        if not targets:
            return error_result(
                "No nParticle shapes found",
                "Create nParticle systems first with create_nparticle_emitter",
            ).to_dict()

        cmds.select(targets, replace=True)

        # Create field — returns list containing the field transform
        field_result = getattr(cmds, ft)(magnitude=magnitude) or []
        field_transform = field_result[0] if field_result else None

        if field_transform and field_name:
            try:
                field_transform = cmds.rename(field_transform, field_name)
            except Exception:
                pass

        # Collect field shape
        field_shapes = []
        if field_transform:
            shapes = cmds.listRelatives(field_transform, shapes=True) or []
            field_shapes = shapes

        return success_result(
            "Added '{}' field to {} nParticle system(s)".format(field_type, len(targets)),
            prompt="Scrub the timeline to see the field affecting the particles.",
            field_transform=field_transform,
            field_shapes=field_shapes,
            field_type=field_type,
            magnitude=magnitude,
            connected_particles=targets,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_field_to_nparticles failed")
        return error_result("Failed to add field '{}'".format(field_type), str(exc)).to_dict()


def main(**kwargs):
    return add_field_to_nparticles(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(add_field_to_nparticles(field_type="gravity")))
