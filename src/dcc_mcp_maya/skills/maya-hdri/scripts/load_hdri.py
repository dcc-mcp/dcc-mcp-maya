"""Load an HDR image as an IBL environment light."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def load_hdri(
    file_path: str,
    use_arnold: bool = True,
    exposure: float = 0.0,
    rotation_y: float = 0.0,
    name: str = "hdriDome1",
) -> dict:
    """Load an HDR image and create an IBL dome light.

    When Arnold is available the function creates an ``aiSkyDomeLight`` with a
    linked ``file`` texture; otherwise it falls back to a native Maya
    ``ambientLight`` node with a connected file texture.

    Args:
        file_path: Absolute path to the ``.hdr`` or ``.exr`` file.
        use_arnold: Try to create an Arnold ``aiSkyDomeLight`` first.  Falls back
            to native Maya IBL when Arnold is not loaded.  Default: ``True``.
        exposure: Initial exposure value (additive, in stops).  Default: ``0.0``.
        rotation_y: Initial Y-axis rotation in degrees.  Default: ``0.0``.
        name: Name for the created light transform.  Default: ``"hdriDome1"``.

    Returns:
        ActionResultModel dict with ``light_node``, ``file_node``, ``backend``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not os.path.isfile(file_path):
            return maya_error(
                "HDRI file not found: {}".format(file_path),
                "Ensure the file path is correct and accessible",
            )

        backend = "native"
        light_transform = ""
        file_node = ""

        if use_arnold:
            try:
                cmds.loadPlugin("mtoa", quiet=True)
                dome = cmds.shadingNode("aiSkyDomeLight", asLight=True, name=name)
                light_transform = dome
                # Create a file texture and connect it
                file_node = cmds.shadingNode("file", asTexture=True, name="{}_tex".format(name))
                cmds.setAttr("{}.fileTextureName".format(file_node), file_path, type="string")
                cmds.connectAttr(
                    "{}.outColor".format(file_node),
                    "{}.color".format(dome),
                    force=True,
                )
                if cmds.attributeQuery("aiExposure", node=dome, exists=True):
                    cmds.setAttr("{}.aiExposure".format(dome), exposure)
                cmds.setAttr("{}.rotateY".format(dome), rotation_y)
                backend = "arnold"
            except Exception:
                # Arnold not available; fall through to native
                try:
                    cmds.delete(light_transform)
                except Exception:
                    pass
                light_transform = ""
                file_node = ""

        if backend == "native" or not light_transform:
            # Fallback: native ambientLight
            light_transform = cmds.directionalLight(name=name, rotation=[0, rotation_y, 0])
            file_node = cmds.shadingNode("file", asTexture=True, name="{}_tex".format(name))
            cmds.setAttr("{}.fileTextureName".format(file_node), file_path, type="string")
            backend = "native"

        return maya_success(
            "HDRI loaded from '{}' using {} backend".format(os.path.basename(file_path), backend),
            prompt="Use set_hdri_exposure or set_hdri_rotation to fine-tune the environment.",
            light_node=light_transform,
            file_node=file_node,
            backend=backend,
            file_path=file_path,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to load HDRI")


def main(**kwargs):
    return load_hdri(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(load_hdri("/path/to/env.hdr")))
