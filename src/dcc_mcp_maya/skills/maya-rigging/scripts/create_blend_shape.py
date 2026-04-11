"""Create a blend shape deformer on a base mesh with optional targets."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_blend_shape(
    base_mesh: str,
    target_meshes: Optional[List[str]] = None,
    name: Optional[str] = None,
    origin: str = "local",
) -> dict:
    """Create a blend shape deformer on a base mesh with optional targets.

    Args:
        base_mesh: Name of the base (destination) mesh.
        target_meshes: List of target mesh names whose shapes drive the blend.
            If None or empty, a zero-target blend shape node is created.
        name: Optional name for the blend shape node.
        origin: ``"local"`` (default) or ``"world"`` space blend.

    Returns:
        ActionResultModel dict with ``context.blend_shape_name``,
        ``context.target_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, base_mesh)
        if err:
            return err

        targets = target_meshes or []
        missing = [t for t in targets if not cmds.objExists(t)]
        if missing:
            return skill_error(
                "Target meshes not found: {}".format(", ".join(missing)),
                "The following targets do not exist: {}".format(", ".join(missing)),
            )

        all_meshes = targets + [base_mesh]
        kwargs = {"origin": origin}  # type: dict
        if name:
            kwargs["name"] = name

        result = cmds.blendShape(*all_meshes, **kwargs)
        bs_name = result[0] if result else (name or "blendShape1")

        return skill_success(
            "Created blend shape '{}' on '{}'".format(bs_name, base_mesh),
            blend_shape_name=bs_name,
            base_mesh=base_mesh,
            target_count=len(targets),
            targets=targets,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create blend shape on {}".format(base_mesh))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_blend_shape`."""
    return create_blend_shape(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
