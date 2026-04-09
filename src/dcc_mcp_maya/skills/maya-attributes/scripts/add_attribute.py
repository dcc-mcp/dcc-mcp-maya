"""Add a custom attribute to a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Supported attribute type tokens for addAttr -attributeType / -dataType
_SCALAR_TYPES = ("bool", "byte", "short", "long", "float", "double", "angle", "time")
_STRING_TYPES = ("string",)
_VECTOR_TYPES = ("float2", "float3", "double2", "double3")


def add_attribute(
    object_name: str,
    long_name: str,
    attr_type: str = "double",
    short_name: Optional[str] = None,
    default_value: Any = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    keyable: bool = True,
) -> dict:
    """Add a custom attribute to a Maya node.

    Supports scalar numeric types, boolean, string, and 2/3-component vector
    types.  The attribute is made keyable by default.

    Args:
        object_name: Name of the Maya node to receive the attribute.
        long_name: Long name for the attribute (e.g. ``"myCustomAttr"``).
        attr_type: Attribute type token.  Supported values: ``"bool"``,
            ``"byte"``, ``"short"``, ``"long"``, ``"float"``, ``"double"``
            (default), ``"angle"``, ``"time"``, ``"string"``,
            ``"float2"``, ``"float3"``, ``"double2"``, ``"double3"``.
        short_name: Optional short name (alias).  Defaults to the first 3
            characters of *long_name*.
        default_value: Default value for numeric/bool attributes.  Ignored
            for string and vector types.
        min_value: Optional minimum for numeric attributes.
        max_value: Optional maximum for numeric attributes.
        keyable: Whether to mark the attribute keyable.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.long_name``, ``context.attr_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if cmds.objExists("{}.{}".format(object_name, long_name)):
            return error_result(
                "Attribute already exists: {}.{}".format(object_name, long_name),
                "Delete the existing attribute first or use a different long_name",
            ).to_dict()

        sn = short_name if short_name else long_name[:3]

        kwargs = {}  # type: dict

        if attr_type in _STRING_TYPES:
            # dataType attribute
            cmds.addAttr(object_name, longName=long_name, shortName=sn, dataType="string")
        elif attr_type in _VECTOR_TYPES:
            # compound numeric attribute (no default/min/max for compound itself)
            cmds.addAttr(object_name, longName=long_name, shortName=sn, attributeType=attr_type)
        else:
            if attr_type not in _SCALAR_TYPES:
                return error_result(
                    "Unsupported attribute type: {}".format(attr_type),
                    "Supported types: {}".format(
                        ", ".join(list(_SCALAR_TYPES) + list(_STRING_TYPES) + list(_VECTOR_TYPES))
                    ),
                ).to_dict()

            if default_value is not None:
                kwargs["defaultValue"] = float(default_value)
            if min_value is not None:
                kwargs["minValue"] = float(min_value)
            if max_value is not None:
                kwargs["maxValue"] = float(max_value)

            cmds.addAttr(object_name, longName=long_name, shortName=sn, attributeType=attr_type, **kwargs)

        # Make keyable (only applicable to DG attributes, not compound children)
        full_attr = "{}.{}".format(object_name, long_name)
        if cmds.objExists(full_attr):
            cmds.setAttr(full_attr, keyable=keyable)

        return success_result(
            "Added attribute '{}.{}'".format(object_name, long_name),
            object_name=object_name,
            long_name=long_name,
            short_name=sn,
            attr_type=attr_type,
            keyable=keyable,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_attribute failed")
        return error_result("Failed to add attribute '{}.{}'".format(object_name, long_name), str(exc)).to_dict()



def main(**kwargs):
    return add_attribute(**kwargs)


if __name__ == "__main__":
    import json
    result = add_attribute()
    print(json.dumps(result))
