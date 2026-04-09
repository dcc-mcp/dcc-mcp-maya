"""List attributes on a Maya node."""

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


def list_attributes(
    object_name: str,
    user_defined: bool = False,
    keyable: bool = False,
    scalar_only: bool = False,
) -> dict:
    """List attributes on a Maya node.

    Args:
        object_name: Name of the Maya node.
        user_defined: If True, return only user-defined (custom) attributes.
            Default: False (return all attributes).
        keyable: If True, return only keyable attributes.  Mutually inclusive
            with *user_defined*.
        scalar_only: If True, skip compound/multi attributes that cannot be
            set with a single scalar value.

    Returns:
        ActionResultModel dict with ``context.attributes`` — list of dicts
        with ``name``, ``type``, ``value``, ``keyable``, ``locked`` keys.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        # Build query kwargs
        list_kwargs = {}  # type: dict
        if user_defined:
            list_kwargs["userDefined"] = True
        if keyable:
            list_kwargs["keyable"] = True

        raw_names = cmds.listAttr(object_name, **list_kwargs) or []

        result = []  # type: List[dict]
        for attr_name in raw_names:
            full_attr = "{}.{}".format(object_name, attr_name)
            if not cmds.objExists(full_attr):
                continue
            try:
                attr_type = cmds.getAttr(full_attr, type=True) or "unknown"
                is_keyable = bool(cmds.getAttr(full_attr, keyable=True))
                is_locked = bool(cmds.getAttr(full_attr, lock=True))

                # Optionally skip compound / multi
                if scalar_only:
                    try:
                        raw_val = cmds.getAttr(full_attr)
                        if isinstance(raw_val, list) and raw_val and isinstance(raw_val[0], tuple):
                            continue
                    except Exception:
                        continue

                try:
                    raw_val = cmds.getAttr(full_attr)
                    if isinstance(raw_val, list) and raw_val and isinstance(raw_val[0], tuple):
                        value = list(raw_val[0])
                    else:
                        value = raw_val
                except Exception:
                    value = None

                result.append(
                    {
                        "name": attr_name,
                        "type": attr_type,
                        "value": value,
                        "keyable": is_keyable,
                        "locked": is_locked,
                    }
                )
            except Exception:
                result.append({"name": attr_name, "type": "unknown", "value": None, "keyable": False, "locked": False})

        return success_result(
            "Found {} attribute(s) on '{}'".format(len(result), object_name),
            object_name=object_name,
            attributes=result,
            count=len(result),
            user_defined_only=user_defined,
            keyable_only=keyable,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_attributes failed")
        return error_result("Failed to list attributes on '{}'".format(object_name), str(exc)).to_dict()



def main(**kwargs):
    return list_attributes(**kwargs)


if __name__ == "__main__":
    import json
    result = list_attributes()
    print(json.dumps(result))
