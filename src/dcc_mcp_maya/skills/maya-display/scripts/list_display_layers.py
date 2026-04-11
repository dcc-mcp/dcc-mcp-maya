"""List all display layers in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_display_layers() -> dict:
    """List all display layers in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.layers`` — a list of dicts
        containing ``name``, ``visibility``, and ``members``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        raw = cmds.ls(type="displayLayer") or []
        layers = []
        for layer in raw:
            vis = bool(cmds.getAttr("{}.visibility".format(layer)))
            members = cmds.editDisplayLayerMembers(layer, query=True, fullNames=True) or []
            layers.append(
                {
                    "name": layer,
                    "visibility": vis,
                    "members": list(members),
                }
            )

        return skill_success(
            "Found {} display layer(s)".format(len(layers)),
            prompt="Use create_display_layer to add a new layer or set_display_layer to move objects.",
            layers=layers,
            count=len(layers),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list display layers")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_display_layers`."""
    return list_display_layers(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
