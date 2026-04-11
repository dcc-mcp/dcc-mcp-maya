"""Transfer mesh attributes (UVs, normals, vertex colors) from one mesh to another."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def transfer_attributes(
    source: str,
    target: str,
    sample_space: int = 0,
    transfer_positions: bool = False,
    transfer_normals: bool = True,
    transfer_uvs: bool = True,
    transfer_colors: bool = False,
) -> dict:
    """Transfer mesh attributes (UVs, normals, vertex colors) from one mesh to another.

    Uses ``cmds.transferAttributes`` to copy surface data between two polygon
    meshes that share a similar topology or surface shape.

    Args:
        source: Name of the *source* mesh (or its transform).
        target: Name of the *target* mesh (or its transform) that will
            receive the transferred data.
        sample_space: Space used for attribute sampling:
            ``0`` = World space (default), ``1`` = Local space,
            ``4`` = UV space, ``5`` = Component space.
        transfer_positions: If True, transfer vertex positions.
            Default: False.
        transfer_normals: If True, transfer vertex normals.  Default: True.
        transfer_uvs: If True, transfer UV sets.  Default: True.
        transfer_colors: If True, transfer vertex color sets.  Default: False.

    Returns:
        ActionResultModel dict with ``context.source``, ``context.target``,
        ``context.transfer_node`` (the created ``transferAttributes`` node).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_SPACES = (0, 1, 4, 5)

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source):
            return error_result(
                "Source not found: {}".format(source),
                "'{}' does not exist in the scene".format(source),
            ).to_dict()

        if not cmds.objExists(target):
            return error_result(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            ).to_dict()

        if sample_space not in _VALID_SPACES:
            return error_result(
                "Invalid sample_space: {}".format(sample_space),
                "sample_space must be one of {} (0=World, 1=Local, 4=UV, 5=Component)".format(_VALID_SPACES),
            ).to_dict()

        result = cmds.transferAttributes(
            source,
            target,
            transferPositions=int(transfer_positions),
            transferNormals=int(transfer_normals),
            transferUVs=int(transfer_uvs),
            transferColors=int(transfer_colors),
            sampleSpace=sample_space,
        )
        node_name = result[0] if result else "transferAttributes1"

        return success_result(
            "Transferred attributes from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            transfer_node=node_name,
            sample_space=sample_space,
            transfer_positions=transfer_positions,
            transfer_normals=transfer_normals,
            transfer_uvs=transfer_uvs,
            transfer_colors=transfer_colors,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("transfer_attributes failed")
        return error_result(
            "Failed to transfer attributes from '{}' to '{}'".format(source, target), str(exc)
        ).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`transfer_attributes`."""
    return transfer_attributes(**kwargs)


if __name__ == "__main__":
    import json

    result = transfer_attributes()
    print(json.dumps(result))
