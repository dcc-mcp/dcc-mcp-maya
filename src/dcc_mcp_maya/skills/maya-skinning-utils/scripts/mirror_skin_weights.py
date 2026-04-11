"""Mirror skin weights across an axis plane."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def mirror_skin_weights(
    mesh: str,
    mirror_mode: str = "YZ",
    surface_association: str = "closestPoint",
    influence_association: str = "closestJoint",
    positive_to_negative: bool = True,
) -> dict:
    """Mirror skin weights across an axis plane.

    Args:
        mesh: Name of the skinned mesh.
        mirror_mode: Mirror plane: ``YZ`` (default, mirrors along X),
            ``XY`` (mirrors along Z), ``XZ`` (mirrors along Y).
        surface_association: Surface point matching method:
            ``closestPoint`` (default), ``rayCast``, ``closestComponent``.
        influence_association: Joint matching method:
            ``closestJoint`` (default), ``closestBone``, ``label``, ``name``.
        positive_to_negative: If True, copy from positive to negative side;
            if False, copy from negative to positive.

    Returns:
        ActionResultModel dict with ``context.skin_cluster_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        sc_list = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster")
        if not sc_list:
            return skill_error(
                "No skin cluster on: {}".format(mesh),
                "'{}' has no skinCluster in its history".format(mesh),
            )

        sc = sc_list[0]

        mirror_kwargs = {
            "mirrorMode": mirror_mode,
            "surfaceAssociation": surface_association,
            "influenceAssociation": influence_association,
        }  # type: dict

        if positive_to_negative:
            mirror_kwargs["mirrorInverse"] = False
        else:
            mirror_kwargs["mirrorInverse"] = True

        cmds.copySkinWeights(
            mesh, mirrorMode=mirror_mode, **{k: v for k, v in mirror_kwargs.items() if k != "mirrorMode"}
        )

        return skill_success(
            "Mirrored skin weights on '{}' across {} plane".format(mesh, mirror_mode),
            prompt="Check the mirrored side in the component editor to verify weight accuracy.",
            mesh=mesh,
            skin_cluster_name=sc,
            mirror_mode=mirror_mode,
            positive_to_negative=positive_to_negative,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to mirror skin weights on '{}'".format(mesh))


@skill_entry
def main(**kwargs):
    return mirror_skin_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
