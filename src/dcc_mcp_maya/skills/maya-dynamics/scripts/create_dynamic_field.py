"""Create a Maya dynamic field and optionally connect it to objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def create_dynamic_field(
    field_type: str = "gravity",
    name: Optional[str] = None,
    magnitude: float = 9.8,
    objects: Optional[List[str]] = None,
) -> dict:
    """Create a Maya dynamic field and optionally connect it to objects.

    Supported field types: ``gravity``, ``turbulence``, ``radial``,
    ``uniform``, ``vortex``, ``drag``, ``newton``, ``air``.

    Args:
        field_type: Type of dynamic field to create.  Default: ``"gravity"``.
        name: Optional name for the field node.  Maya auto-names if ``None``.
        magnitude: Field strength/magnitude.  Default: ``9.8``.
        objects: Optional list of particle/nParticle system names to connect
            the field to via ``cmds.connectDynamic(fields=...)``.

    Returns:
        ActionResultModel dict with ``context.field_node``,
        ``context.field_type``, ``context.magnitude``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    ft = field_type.lower()
    if ft not in _VALID_FIELD_TYPES:
        return error_result(
            "Invalid field type: {}".format(field_type),
            "Supported types: {}".format(", ".join(_VALID_FIELD_TYPES)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        create_fn = getattr(cmds, ft, None)
        if create_fn is None:
            return error_result(
                "Field type not available: {}".format(ft),
                "cmds.{} is not accessible in this Maya version".format(ft),
            ).to_dict()

        field_kwargs = {}
        if name:
            field_kwargs["name"] = name

        result = create_fn(**field_kwargs)
        field_node = result[0] if isinstance(result, (list, tuple)) else result

        # Set magnitude
        mag_attr = "{}.magnitude".format(field_node)
        if cmds.objExists(mag_attr):
            cmds.setAttr(mag_attr, magnitude)

        # Connect to particle systems
        connected = []
        if objects:
            missing = [o for o in objects if not cmds.objExists(o)]
            if missing:
                return error_result(
                    "Object(s) not found: {}".format(", ".join(missing)),
                    "Ensure all objects exist before connecting the field",
                ).to_dict()
            cmds.connectDynamic(objects, fields=field_node)
            connected = list(objects)

        return success_result(
            "Created {} field '{}'".format(ft, field_node),
            field_node=field_node,
            field_type=ft,
            magnitude=magnitude,
            connected_objects=connected,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_dynamic_field failed")
        return error_result("Failed to create dynamic field", str(exc)).to_dict()


def main(**kwargs):
    return create_dynamic_field(**kwargs)


if __name__ == "__main__":
    import json

    result = create_dynamic_field()
    print(json.dumps(result))
