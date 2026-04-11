"""Convert the current selection to a different component type."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_CONVERT_FLAGS = {
    "vertex": {"toVertex": True},
    "edge": {"toEdge": True},
    "face": {"toFace": True},
    "uv": {"toUV": True},
    "object": {"toObject": True},
    "shell": {"toShell": True},
}


def convert_selection(target: str = "") -> dict:
    """Convert selection to a different component type.

    Args:
        target: Component type to convert to.
            One of: "vertex", "edge", "face", "uv", "object", "shell".

    Returns:
        ActionResultModel dict with ``context.target``, ``context.count``.
    """
    target = target.lower()
    if target not in _CONVERT_FLAGS:
        return skill_error(
            "Invalid target type",
            "'{}' is not a valid target. Choose from: {}".format(
                target, ", ".join(sorted(_CONVERT_FLAGS.keys()))
            ),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        flags = _CONVERT_FLAGS[target]  # noqa: F841
        current = cmds.ls(selection=True) or []
        if not current:
            return skill_error(
                "Nothing selected",
                "Select objects or components before converting",
            )

        if target == "object":
            cmds.select(cmds.ls(selection=True, objectsOnly=True))
        else:
            converted = cmds.polyListComponentConversion(current, **_CONVERT_FLAGS[target]) or []
            if converted:
                cmds.select(converted)

        result = cmds.ls(selection=True, flatten=True) or []
        return skill_success(
            "Converted selection to {} ({} items)".format(target, len(result)),
            prompt="Use grow_selection or shrink_selection to refine the component selection.",
            target=target,
            count=len(result),
            selection=result,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to convert selection")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`convert_selection`."""
    return convert_selection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
