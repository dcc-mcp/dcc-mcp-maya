"""Add a new Arnold AOV to the render settings."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Standard Arnold AOV types
_STANDARD_AOV_TYPES = {
    "beauty": "RGBA",
    "diffuse": "RGB",
    "specular": "RGB",
    "transmission": "RGB",
    "sss": "RGB",
    "volume": "RGB",
    "emission": "RGB",
    "background": "RGB",
    "shadow": "RGB",
    "shadow_matte": "RGBA",
    "Z": "FLOAT",
    "N": "RGB",
    "P": "RGB",
    "motionvector": "RGB",
    "crypto_asset": "FLOAT",
    "crypto_object": "FLOAT",
    "crypto_material": "FLOAT",
}


def add_aov(
    name: str,
    aov_type: Optional[str] = None,
    enabled: bool = True,
) -> dict:
    """Add a new Arnold AOV to the current render settings.

    Creates an ``aiAOV`` node and connects it to the Arnold render options so
    that the named output is written alongside the beauty pass.

    Args:
        name: AOV name (e.g. ``"diffuse"``, ``"Z"``, ``"my_custom_aov"``).
        aov_type: Data type string accepted by Arnold (e.g. ``"RGB"``,
            ``"RGBA"``, ``"FLOAT"``, ``"VECTOR"``).  When not supplied the
            function attempts to infer the type from ``name`` for well-known
            AOVs; falls back to ``"RGB"`` for unknowns.
        enabled: Whether to enable the AOV immediately.  Default: True.

    Returns:
        ToolResult dict with ``context.aov_node``, ``context.aov_type``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return skill_error("AOV name is required", "Provide a non-empty AOV name")

        # Arnold (mtoa) must be loaded to use aiAOV nodes
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            return skill_error(
                "Arnold (mtoa) plugin is not loaded",
                "Load the mtoa plugin first: cmds.loadPlugin('mtoa')",
            )

        # Resolve type — check both original case and lowercase for case-insensitive lookup
        resolved_type = aov_type or _STANDARD_AOV_TYPES.get(name) or _STANDARD_AOV_TYPES.get(name.lower(), "RGB")

        # Check if AOV already exists
        existing = cmds.ls(type="aiAOV") or []
        for node in existing:
            if cmds.getAttr("{}.name".format(node)) == name:
                return skill_error(
                    "AOV '{}' already exists".format(name),
                    "Delete the existing AOV before adding a new one with the same name",
                )

        # Create aiAOV node
        aov_node = cmds.createNode("aiAOV", name="aiAOV_{}".format(name))
        cmds.setAttr("{}.name".format(aov_node), name, type="string")
        cmds.setAttr("{}.type".format(aov_node), _type_to_int(resolved_type))
        cmds.setAttr("{}.enabled".format(aov_node), enabled)

        # Connect to Arnold render options if available
        if cmds.objExists("defaultArnoldRenderOptions"):
            aov_index = _get_next_aov_index(cmds)
            cmds.connectAttr(
                "{}.message".format(aov_node),
                "defaultArnoldRenderOptions.aovList[{}]".format(aov_index),
                force=True,
            )

        return skill_success(
            "Added Arnold AOV '{}' ({})".format(name, resolved_type),
            prompt="Use set_aov_attribute to configure filters or drivers, or enable_aov to toggle it.",
            aov_node=aov_node,
            aov_name=name,
            aov_type=resolved_type,
            enabled=enabled,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add AOV '{}'".format(name))


def _type_to_int(type_str: str) -> int:
    """Map Arnold AOV type string to integer index."""
    _map = {"RGBA": 4, "RGB": 3, "VECTOR": 5, "FLOAT": 1, "INT": 2}
    return _map.get(type_str.upper(), 3)


def _get_next_aov_index(cmds) -> int:  # type: ignore[no-untyped-def]
    """Return the next unused index in the Arnold render options AOV list."""
    existing = cmds.getAttr("defaultArnoldRenderOptions.aovList", multiIndices=True) or []
    return max(existing) + 1 if existing else 0


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_aov`."""
    return add_aov(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
