"""Freeze (apply) the transforms of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


_TOLERANCE = 1e-5


def _vector_attr(cmds, object_name: str, attribute: str) -> list:
    value = cmds.getAttr("{}.{}".format(object_name, attribute))
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
        value = value[0]
    return [float(component) for component in value]


def _matches(actual: list, expected: list) -> bool:
    return len(actual) == 3 and all(abs(actual[index] - expected[index]) <= _TOLERANCE for index in range(3))


def freeze_transforms(object_name: str) -> dict:
    """Freeze (apply) the transforms of an object.

    Zeroes out translate/rotate and sets scale to 1 by baking current
    transform values into the shape.

    Args:
        object_name: Name of the object whose transforms to freeze.

    Returns:
        ToolResult dict.
    """

    mutation_applied = False
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        cmds.makeIdentity(object_name, apply=True, translate=True, rotate=True, scale=True)
        mutation_applied = True
        verified_transform = {
            "translate": _vector_attr(cmds, object_name, "translate"),
            "rotate": _vector_attr(cmds, object_name, "rotate"),
            "scale": _vector_attr(cmds, object_name, "scale"),
        }
        if not (
            _matches(verified_transform["translate"], [0.0, 0.0, 0.0])
            and _matches(verified_transform["rotate"], [0.0, 0.0, 0.0])
            and _matches(verified_transform["scale"], [1.0, 1.0, 1.0])
        ):
            return skill_error(
                "Freeze transform verification failed",
                "Maya did not report identity translate, rotate, and scale values",
                object_name=object_name,
                verified_transform=verified_transform,
                mutation_applied=True,
                rollback_attempted=False,
                rollback_verified=False,
            )
        return skill_success(
            "Transforms frozen on '{}'".format(object_name),
            object_name=object_name,
            verified_transform=verified_transform,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        context = {}
        if mutation_applied:
            context = {
                "mutation_applied": True,
                "rollback_attempted": False,
                "rollback_verified": False,
            }
        return skill_exception(exc, message="Failed to freeze transforms on '{}'".format(object_name), **context)


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`freeze_transforms`."""
    return freeze_transforms(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
