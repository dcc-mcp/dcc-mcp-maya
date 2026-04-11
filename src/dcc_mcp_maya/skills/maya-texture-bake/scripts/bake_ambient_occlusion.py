"""Bake ambient occlusion to a texture using a mib_amb_occlusion shader."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
import os
from typing import List, Optional


def bake_ambient_occlusion(
    objects: Optional[List[str]] = None,
    output_dir: str = "/tmp",
    resolution: int = 1024,
    samples: int = 64,
    max_distance: float = 0.0,
    file_format: str = "png",
) -> dict:
    """Bake ambient occlusion to a texture.

    Creates a temporary ``mib_amb_occlusion`` shader, assigns it to the target
    objects, bakes via ``convertSolidTx``, then restores the original shading.

    Args:
        objects: List of mesh or transform names to bake AO for.  If ``None``,
            uses the current selection.
        output_dir: Directory for output images.  Default: ``"/tmp"``.
        resolution: Texture resolution in pixels (square).  Default: ``1024``.
        samples: Number of AO ray samples.  Default: ``64``.
        max_distance: Maximum ray distance (0 = unlimited).  Default: ``0.0``.
        file_format: Image format.  Default: ``"png"``.

    Returns:
        ActionResultModel dict with ``baked_files``, ``objects``, ``resolution``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or (cmds.ls(selection=True) or [])
        if not targets:
            return maya_error(
                "No objects specified",
                "Provide 'objects' or select meshes",
            )

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # Create AO shader
        ao_shader = cmds.shadingNode("mib_amb_occlusion", asShader=True, name="_tmp_ao_shader")
        cmds.setAttr("{}.samples".format(ao_shader), samples)
        cmds.setAttr("{}.maxDistance".format(ao_shader), max_distance)
        ao_sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="_tmp_ao_sg")
        cmds.connectAttr(
            "{}.outValue".format(ao_shader),
            "{}.surfaceShader".format(ao_sg),
            force=True,
        )

        baked_files = []
        original_assignments = {}

        for obj in targets:
            if not cmds.objExists(obj):
                continue
            # Record current shader assignment
            sgs = (
                cmds.listConnections(
                    cmds.listHistory(obj, pruneDagObjects=True) or [],
                    type="shadingEngine",
                )
                or []
            )
            original_assignments[obj] = sgs[0] if sgs else "initialShadingGroup"

            out_file = os.path.join(output_dir, "{}_ao.{}".format(obj.replace(":", "_"), file_format))
            cmds.sets(obj, edit=True, forceElement=ao_sg)
            cmds.convertSolidTx(
                ao_shader,
                obj,
                fileFormat=file_format,
                fileImageName=out_file,
                resolutionX=resolution,
                resolutionY=resolution,
                antiAlias=True,
            )
            baked_files.append(out_file)

        # Restore original shader assignments
        for obj, sg in original_assignments.items():
            try:
                cmds.sets(obj, edit=True, forceElement=sg)
            except Exception:
                pass

        # Clean up temp nodes
        try:
            cmds.delete(ao_sg, ao_shader)
        except Exception:
            pass

        return maya_success(
            "Baked AO for {} object(s)".format(len(baked_files)),
            prompt="Use bake_lighting to bake full lighting or transfer_maps for normals.",
            baked_files=baked_files,
            objects=targets,
            resolution=resolution,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to bake ambient occlusion")


def main(**kwargs):
    return bake_ambient_occlusion(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(bake_ambient_occlusion(["pSphere1"], output_dir="/tmp")))
