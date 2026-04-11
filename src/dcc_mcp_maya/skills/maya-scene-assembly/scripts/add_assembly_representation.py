"""Add a representation (LOD) to a Maya assembly definition."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

_VALID_TYPES = {"Locator", "Cache", "GPU", "Scene"}


def add_assembly_representation(
    assembly: str,
    rep_type: str,
    rep_name: Optional[str] = None,
    file_path: Optional[str] = None,
) -> dict:
    """Add a representation to an assembly definition.

    Args:
        assembly: Assembly definition node name.
        rep_type: Representation type: ``"Locator"``, ``"Cache"``, ``"GPU"``, or ``"Scene"``.
        rep_name: Optional name for this representation.
        file_path: Optional file path for Cache/GPU/Scene representations.

    Returns:
        ActionResultModel dict with ``context.rep_node`` and ``context.rep_type``.
    """

    if rep_type not in _VALID_TYPES:
        return maya_error(
            "Invalid rep_type '{}'. Valid types: {}".format(rep_type, sorted(_VALID_TYPES)),
            "Choose one of: Locator, Cache, GPU, Scene.",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(assembly):
            return maya_error(
                "Assembly '{}' not found".format(assembly),
                "Use list_assemblies or create_assembly_definition first.",
            )

        kwargs = {"input": assembly, "type": rep_type}
        if rep_name:
            kwargs["repName"] = rep_name

        rep_node = cmds.assembly(**kwargs)

        if file_path and rep_node:
            try:
                cmds.setAttr("{}.definition".format(rep_node), file_path, type="string")
            except Exception:
                pass

        return maya_success(
            "Added '{}' representation to '{}'".format(rep_type, assembly),
            prompt="Representation added. Use create_assembly_reference to instance this definition.",
            assembly=assembly,
            rep_node=rep_node,
            rep_type=rep_type,
            file_path=file_path or "",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add representation")


def main(**kwargs):
    return add_assembly_representation(**kwargs)


if __name__ == "__main__":
    import json

    result = add_assembly_representation("asm1", "Locator")
    print(json.dumps(result))
