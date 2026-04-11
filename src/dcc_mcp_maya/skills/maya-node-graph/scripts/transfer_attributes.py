"""Transfer mesh attributes (UVs, normals, vertex colors) from one mesh to another."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success


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

    _VALID_SPACES = (0, 1, 4, 5)

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(source):
            return maya_error(
                "Source not found: {}".format(source),
                "'{}' does not exist in the scene".format(source),
            )

        if not cmds.objExists(target):
            return maya_error(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            )

        if sample_space not in _VALID_SPACES:
            return maya_error(
                "Invalid sample_space: {}".format(sample_space),
                "sample_space must be one of {} (0=World, 1=Local, 4=UV, 5=Component)".format(_VALID_SPACES),
            )

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

        return maya_success(
            "Transferred attributes from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            transfer_node=node_name,
            sample_space=sample_space,
            transfer_positions=transfer_positions,
            transfer_normals=transfer_normals,
            transfer_uvs=transfer_uvs,
            transfer_colors=transfer_colors,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error("Failed to transfer attributes from '{}' to '{}'".format(source, target), str(exc))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`transfer_attributes`."""
    return transfer_attributes(**kwargs)


if __name__ == "__main__":
    import json

    result = transfer_attributes()
    print(json.dumps(result))
