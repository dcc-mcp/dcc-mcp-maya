"""Delete an Arnold AOV node by name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def delete_aov(name: str) -> dict:
    """Delete the Arnold AOV node whose ``name`` attribute matches *name*.

    Args:
        name: The AOV name as set in the ``aiAOV.name`` attribute (not the
            Maya node name).

    Returns:
        ActionResultModel dict with ``context.deleted_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name:
            return skill_error("AOV name is required", "Provide a non-empty AOV name")

        nodes = cmds.ls(type="aiAOV") or []
        target_node = None
        for node in nodes:
            try:
                if cmds.getAttr("{}.name".format(node)) == name:
                    target_node = node
                    break
            except Exception:
                pass

        if target_node is None:
            return skill_error(
                "AOV '{}' not found".format(name),
                "No aiAOV node with name '{}' exists in the scene".format(name),
            )

        cmds.delete(target_node)
        return skill_success(
            "Deleted Arnold AOV '{}'".format(name),
            prompt="Use list_aovs to verify the AOV was removed.",
            deleted_node=target_node,
            aov_name=name,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete AOV '{}'".format(name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_aov`."""
    return delete_aov(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
