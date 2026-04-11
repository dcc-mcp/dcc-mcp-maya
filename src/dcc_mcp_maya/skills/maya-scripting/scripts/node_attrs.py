"""Maya custom node attribute actions.

Provides actions for adding, removing and listing custom (user-defined)
attributes on Maya nodes:

- :func:`add_attribute`    — add a custom attribute to a node
- :func:`delete_attribute` — delete a custom attribute from a node
- :func:`list_attributes`  — list attributes on a node (optionally user-defined only)
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Optional

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        if cmds.objExists("{}.{}".format(object_name, long_name)):
            return skill_error(
                "Attribute already exists: {}.{}".format(object_name, long_name),
                "Delete the existing attribute first or use a different long_name",
            )

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
                return skill_error(
                    "Unsupported attribute type: {}".format(attr_type),
                    "Supported types: {}".format(
                        ", ".join(list(_SCALAR_TYPES) + list(_STRING_TYPES) + list(_VECTOR_TYPES))
                    ),
                )

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

        return skill_success(
            "Added attribute '{}.{}'".format(object_name, long_name),
            object_name=object_name,
            long_name=long_name,
            short_name=sn,
            attr_type=attr_type,
            keyable=keyable,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add attribute '{}.{}'".format(object_name, long_name))


def delete_attribute(
    object_name: str,
    attribute: str,
) -> dict:
    """Delete a custom (user-defined) attribute from a Maya node.

    Only user-defined attributes can be deleted.  Attempting to delete a
    built-in attribute (e.g. ``"translateX"``) will return an error.

    Args:
        object_name: Name of the Maya node.
        attribute: Long name of the attribute to delete.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        full_attr = "{}.{}".format(object_name, attribute)
        err = validate_node_exists(cmds, full_attr)
        if err:
            return err

        # Only user-defined attributes have userData / dynamic flag
        user_defined = cmds.listAttr(object_name, userDefined=True) or []
        if attribute not in user_defined:
            return skill_error(
                "Cannot delete built-in attribute: {}.{}".format(object_name, attribute),
                "Only user-defined (custom) attributes can be deleted",
            )

        cmds.deleteAttr(full_attr)
        return skill_success(
            "Deleted attribute '{}.{}'".format(object_name, attribute),
            object_name=object_name,
            attribute=attribute,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete attribute '{}.{}'".format(object_name, attribute))


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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

        return skill_success(
            "Found {} attribute(s) on '{}'".format(len(result), object_name),
            object_name=object_name,
            attributes=result,
            count=len(result),
            user_defined_only=user_defined,
            keyable_only=keyable,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list attributes on '{}'".format(object_name))
