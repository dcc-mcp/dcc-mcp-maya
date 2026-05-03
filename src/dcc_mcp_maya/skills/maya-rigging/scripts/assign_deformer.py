"""Apply a deformer to an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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
        ToolResult dict with ``context.deformer_name``,
        ``context.handle_name`` (for cluster/lattice) if applicable.
    """

    _SUPPORTED = ("cluster", "blendShape", "lattice", "wrap", "bend", "twist", "flare", "sine", "squash", "wave")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        if deformer_type not in _SUPPORTED:
            return skill_error(
                "Unsupported deformer type: {}".format(deformer_type),
                "deformer_type must be one of {}".format(_SUPPORTED),
            )

        cmds.select(object_name, replace=True)

        if deformer_type == "cluster":
            result = cmds.cluster(object_name)
            deformer_name = result[0]
            handle_name = result[1] if len(result) > 1 else None
            return skill_success(
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
            return skill_success(
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
            return skill_success(
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
        return skill_success(
            "Applied {} deformer to '{}'".format(deformer_type, object_name),
            object_name=object_name,
            deformer_name=deformer_name,
            deformer_type=deformer_type,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to assign deformer to {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_deformer`."""
    return assign_deformer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
