"""Apply a deformer to an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _SUPPORTED = ("cluster", "blendShape", "lattice", "wrap", "bend", "twist", "flare", "sine", "squash", "wave")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if deformer_type not in _SUPPORTED:
            return error_result(
                "Unsupported deformer type: {}".format(deformer_type),
                "deformer_type must be one of {}".format(_SUPPORTED),
            ).to_dict()

        cmds.select(object_name, replace=True)

        if deformer_type == "cluster":
            result = cmds.cluster(object_name)
            deformer_name = result[0]
            handle_name = result[1] if len(result) > 1 else None
            return success_result(
                "Applied cluster deformer to '{}'".format(object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                handle_name=handle_name,
                deformer_type=deformer_type,
            ).to_dict()

        if deformer_type == "lattice":
            result = cmds.lattice(object_name)
            deformer_name = result[0]
            return success_result(
                "Applied lattice deformer to '{}'".format(object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                deformer_type=deformer_type,
            ).to_dict()

        if deformer_type in ("bend", "twist", "flare", "sine", "squash", "wave"):
            result = cmds.nonLinear(object_name, type=deformer_type)
            deformer_name = result[0]
            handle_name = result[1] if len(result) > 1 else None
            return success_result(
                "Applied {} deformer to '{}'".format(deformer_type, object_name),
                object_name=object_name,
                deformer_name=deformer_name,
                handle_name=handle_name,
                deformer_type=deformer_type,
            ).to_dict()

        # blendShape / wrap — generic path
        result = cmds.deformer(object_name, type=deformer_type)
        deformer_name = result[0] if result else deformer_type
        return success_result(
            "Applied {} deformer to '{}'".format(deformer_type, object_name),
            object_name=object_name,
            deformer_name=deformer_name,
            deformer_type=deformer_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("assign_deformer failed")
        return error_result("Failed to assign deformer to {}".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_deformer`."""
    return assign_deformer(**kwargs)


if __name__ == "__main__":
    import json

    result = assign_deformer()
    print(json.dumps(result))
