"""Set and verify the rotate and scale pivots of a Maya transform."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._mutation import MayaUndoChunk

_TOLERANCE = 1e-5


def _pivots(cmds, object_name, space_flag):
    # type: (...) -> tuple
    values = cmds.xform(object_name, query=True, pivots=True, **space_flag) or []
    if len(values) < 6:
        raise RuntimeError("Maya did not return both rotate and scale pivots")
    return [float(value) for value in values[:3]], [float(value) for value in values[3:6]]


def set_pivot(
    object_name,  # type: str
    position,  # type: List[float]
    space="world",  # type: str
):
    # type: (...) -> dict
    """Set both Maya pivots and fail if their readback differs."""
    if not isinstance(object_name, str) or not object_name:
        return skill_error("Invalid pivot object", "object_name must be a non-empty string")
    if (
        not isinstance(position, list)
        or len(position) != 3
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in position)
    ):
        return skill_error("Invalid pivot position", "position must contain exactly three numbers")
    if space not in ("world", "object"):
        return skill_error("Invalid pivot space", "space must be 'world' or 'object'", space=space)

    expected = [float(value) for value in position]
    transaction = None
    old_rotate_pivot = None
    old_scale_pivot = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Pivot object not found", "'{}' does not exist".format(object_name))

        space_flag = {"worldSpace": True} if space == "world" else {"objectSpace": True}
        old_rotate_pivot, old_scale_pivot = _pivots(cmds, object_name, space_flag)
        transaction = MayaUndoChunk(cmds, "dcc_mcp_set_pivot")
        transaction.begin()
        cmds.xform(object_name, pivots=expected, **space_flag)
        rotate_pivot, scale_pivot = _pivots(cmds, object_name, space_flag)
        matches = all(abs(rotate_pivot[index] - expected[index]) <= _TOLERANCE for index in range(3)) and all(
            abs(scale_pivot[index] - expected[index]) <= _TOLERANCE for index in range(3)
        )
        if not matches:
            receipt = transaction.rollback(
                lambda: _pivots(cmds, object_name, space_flag) == (old_rotate_pivot, old_scale_pivot)
            )
            return skill_error(
                "Pivot verification failed",
                "Maya did not retain the requested rotate and scale pivots",
                object_name=object_name,
                requested_position=expected,
                rotate_pivot=rotate_pivot,
                scale_pivot=scale_pivot,
                space=space,
                **receipt,
            )

        transaction.commit()
        return skill_success(
            "Set and verified pivot on '{}'".format(object_name),
            object_name=object_name,
            rotate_pivot=rotate_pivot,
            scale_pivot=scale_pivot,
            space=space,
            prompt="Use array_instances or freeze_transforms to continue the modeling workflow.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        receipt = {}
        if transaction is not None and old_rotate_pivot is not None and old_scale_pivot is not None:
            receipt = transaction.rollback(
                lambda: _pivots(cmds, object_name, space_flag) == (old_rotate_pivot, old_scale_pivot)
            )
        return skill_exception(exc, message="Failed to set pivot on '{}'".format(object_name), **receipt)


@skill_entry
def main(**kwargs):
    # type: (...) -> dict
    """Entry point; delegates to :func:`set_pivot`."""
    return set_pivot(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
