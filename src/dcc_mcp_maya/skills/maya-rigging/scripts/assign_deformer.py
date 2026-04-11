"""Apply a deformer to an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules


def assign_deformer(
    object_name: str,
    deformer_type: str = "cluster",
) -> dict:
    """Apply a deformer to an object.

    Supported deformer types: ``"cluster"``, ``"blendShape"``, ``"lattice"``,
    ``"wrap"``, ``"nonLinear"`` (bend/twist/flare/sine/squash/wave).

    Args:
        object_name: Name of the mesh/surface to deform.
        deformer_type: Deformer type string.  Default: ``"cluster"``.

    Returns:
        ActionResultModel dict with ``context.deformer_name``,
        ``context.handle_name`` (for cluster/lattice) if applicable.
    """

    _SUPPORTED = ("cluster", "blendShape", "lattice", "wrap", "bend", "twist", "flare", "sine", "squash", "wave")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if deformer_type not in _SUPPORTED:
            return maya_error(
                "Unsupported deformer type: {}".format(deformer_type),
                "deformer_type must be one of {}".format(_SUPPORTED),
            )

        cmds.select(object_name, replace=True)

        if deformer_type == "cluster":
            result = cmds.cluster(object_name)
            deformer_name = result[0]
            handle_name = result[1] if len(result) > 1 else None
            return maya_success(
                "Applied cluster deformer to '{}'".format(object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                handle_name=handle_name,
                deformer_type=deformer_type,
                prompt="Check the result with list_rigging or use related actions to continue.",
            )

        if deformer_type == "lattice":
            result = cmds.lattice(object_name)
            deformer_name = result[0]
            return maya_success(
                "Applied lattice deformer to '{}'".format(object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                deformer_type=deformer_type,
                prompt="Check the result with list_rigging or use related actions to continue.",
            )

        if deformer_type in ("bend", "twist", "flare", "sine", "squash", "wave"):
            result = cmds.nonLinear(object_name, type=deformer_type)
            deformer_name = result[0]
            handle_name = result[1] if len(result) > 1 else None
            return maya_success(
                "Applied {} deformer to '{}'".format(deformer_type, object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                handle_name=handle_name,
                deformer_type=deformer_type,
                prompt="Check the result with list_rigging or use related actions to continue.",
            )

        # blendShape / wrap — generic path
        result = cmds.deformer(object_name, type=deformer_type)
        deformer_name = result[0] if result else deformer_type
        return maya_success(
            "Applied {} deformer to '{}'".format(deformer_type, object_name),
            object_name=object_name,
            deformer_name=deformer_name,
            deformer_type=deformer_type,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to assign deformer to {}".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_deformer`."""
    return assign_deformer(**kwargs)


if __name__ == "__main__":
    import json

    result = assign_deformer()
    print(json.dumps(result))
