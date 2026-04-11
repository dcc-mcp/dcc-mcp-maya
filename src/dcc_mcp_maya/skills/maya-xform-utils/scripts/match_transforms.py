"""Match the position/rotation/scale of one object to another."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def match_transforms(
    source: str,
    target: str,
    translate: bool = True,
    rotate: bool = True,
    scale: bool = False,
) -> dict:
    """Snap *source* object's transforms to match *target*.

    Args:
        source: Name of the object to move/rotate/scale.
        target: Name of the reference object to match against.
        translate: Copy world-space translation if ``True``.
        rotate: Copy world-space rotation if ``True``.
        scale: Copy world-space scale if ``True``.

    Returns:
        ActionResultModel dict with the new ``context.translate``,
        ``context.rotate``, and ``context.scale`` of *source*.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (source, target):
            err = validate_node_exists(cmds, name)
            if err:
                return err

        if translate:
            pos = cmds.xform(target, query=True, worldSpace=True, translation=True)
            cmds.xform(source, worldSpace=True, translation=pos)

        if rotate:
            rot = cmds.xform(target, query=True, worldSpace=True, rotation=True)
            cmds.xform(source, worldSpace=True, rotation=rot)

        if scale:
            scl = cmds.xform(target, query=True, worldSpace=True, scale=True)
            cmds.xform(source, worldSpace=True, scale=scl)

        # Query final state
        new_t = cmds.xform(source, query=True, worldSpace=True, translation=True)
        new_r = cmds.xform(source, query=True, worldSpace=True, rotation=True)
        new_s = cmds.xform(source, query=True, worldSpace=True, scale=True)

        return skill_success(
            "Matched '{}' to '{}'".format(source, target),
            prompt="Use freeze_transforms to bake the matched position, or parent_object if you want a hierarchy.",
            source=source,
            target=target,
            translate=new_t,
            rotate=new_r,
            scale=new_s,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to match transforms")


@skill_entry
def main(**kwargs):
    return match_transforms(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
