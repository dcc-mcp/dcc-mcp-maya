"""Configure output path and image format for a render pass."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_render_pass_output(
    pass_node: str,
    output_path: Optional[str] = None,
    image_format: Optional[str] = None,
) -> dict:
    """Configure output path and image format for a render pass element.

    Args:
        pass_node: Name of the renderPass or aiAOV node.
        output_path: Output file path or token string (e.g.
            ``images/<RenderLayer>/<RenderPass>``).  Only applied when
            the node exposes a ``fileNamePrefix`` or ``outputPrefix``
            attribute.
        image_format: Image format string (e.g. ``exr``, ``png``, ``tif``).
            Only applied when the node exposes a ``imageFormat`` or
            ``dataType`` attribute.

    Returns:
        ActionResultModel dict with ``context.pass_node``,
        ``context.output_path``, and ``context.image_format``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(pass_node):
            return maya_error(
                "Render pass not found: {}".format(pass_node),
                "'{}' does not exist in the scene".format(pass_node),
            )

        changes = []

        if output_path is not None:
            for attr in ("fileNamePrefix", "outputPrefix", "prefix"):
                if cmds.attributeQuery(attr, node=pass_node, exists=True):
                    cmds.setAttr("{}.{}".format(pass_node, attr), output_path, type="string")
                    changes.append("output_path={}".format(output_path))
                    break

        if image_format is not None:
            for attr in ("imageFormat", "dataType", "format"):
                if cmds.attributeQuery(attr, node=pass_node, exists=True):
                    try:
                        cmds.setAttr("{}.{}".format(pass_node, attr), image_format, type="string")
                    except Exception:
                        cmds.setAttr("{}.{}".format(pass_node, attr), image_format)
                    changes.append("image_format={}".format(image_format))
                    break

        if not changes:
            return maya_success(
                "No settable output attributes found on '{}'".format(pass_node),
                prompt="This pass node may not support output path/format overrides.",
                pass_node=pass_node,
                output_path=output_path,
                image_format=image_format,
            )

        return maya_success(
            "Configured output for '{}': {}".format(pass_node, ", ".join(changes)),
            prompt="Verify render settings and render to confirm the pass outputs correctly.",
            pass_node=pass_node,
            output_path=output_path,
            image_format=image_format,
            applied_changes=changes,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to configure output for '{}'".format(pass_node))


def main(**kwargs):
    return set_render_pass_output(**kwargs)


if __name__ == "__main__":
    import json

    result = set_render_pass_output("diffuse_pass", output_path="images/diffuse", image_format="exr")
    print(json.dumps(result))
