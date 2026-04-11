"""Delete an Arnold AOV node by name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
            return maya_error("AOV name is required", "Provide a non-empty AOV name")

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
            return maya_error(
                "AOV '{}' not found".format(name),
                "No aiAOV node with name '{}' exists in the scene".format(name),
            )

        cmds.delete(target_node)
        return maya_success(
            "Deleted Arnold AOV '{}'".format(name),
            prompt="Use list_aovs to verify the AOV was removed.",
            deleted_node=target_node,
            aov_name=name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete AOV '{}'".format(name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_aov`."""
    return delete_aov(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_aov("diffuse")
    print(json.dumps(result))
