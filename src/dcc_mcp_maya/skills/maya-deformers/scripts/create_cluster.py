"""Create a cluster deformer on one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one object name in the 'objects' list",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist before creating a cluster",
            ).to_dict()

        kwargs = {"relative": relative}  # type: Dict
        if name:
            kwargs["name"] = name

        result = cmds.cluster(objects, **kwargs)
        # cmds.cluster returns [clusterNode, clusterHandle]
        cluster_node = result[0] if result else None
        cluster_handle = result[1] if result and len(result) > 1 else None

        return success_result(
            "Created cluster deformer '{}' on {} object(s)".format(cluster_node, len(objects)),
            cluster_node=cluster_node,
            cluster_handle=cluster_handle,
            objects=objects,
            relative=relative,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_cluster failed")
        return error_result("Failed to create cluster deformer", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_cluster`."""
    return create_cluster(**kwargs)


if __name__ == "__main__":
    import json

    result = create_cluster()
    print(json.dumps(result))
