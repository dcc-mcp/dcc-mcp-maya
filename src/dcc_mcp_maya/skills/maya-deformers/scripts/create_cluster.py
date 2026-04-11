"""Create a cluster deformer on one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


def create_cluster(
    objects: List[str],
    name: Optional[str] = None,
    relative: bool = False,
) -> dict:
    """Create a cluster deformer on one or more objects.

    Args:
        objects: List of mesh names to deform.
        name: Optional name for the cluster handle.  Maya auto-names if
            ``None``.
        relative: When ``True``, the cluster operates in relative mode
            (deformation relative to the cluster handle pivot).

    Returns:
        ActionResultModel dict with ``context.cluster_node``,
        ``context.cluster_handle``.
    """
    if not objects:
        return skill_error(
            "No objects specified",
            "Provide at least one object name in the 'objects' list",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, list(objects))
        if err:
            return err

        kwargs = {"relative": relative}  # type: Dict
        if name:
            kwargs["name"] = name

        result = cmds.cluster(objects, **kwargs)
        # cmds.cluster returns [clusterNode, clusterHandle]
        cluster_node = result[0] if result else None
        cluster_handle = result[1] if result and len(result) > 1 else None

        return skill_success(
            "Created cluster deformer '{}' on {} object(s)".format(cluster_node, len(objects)),
            cluster_node=cluster_node,
            cluster_handle=cluster_handle,
            objects=objects,
            relative=relative,
            prompt="Check the result with list_deformers or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create cluster deformer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_cluster`."""
    return create_cluster(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
