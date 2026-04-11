"""List all Arnold AOVs currently defined in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


_INT_TO_TYPE = {1: "FLOAT", 2: "INT", 3: "RGB", 4: "RGBA", 5: "VECTOR"}


def list_aovs() -> dict:
    """List all Arnold AOV nodes (``aiAOV``) in the current scene.

    Returns:
        ActionResultModel dict with ``context.aovs`` (list of dicts with
        ``name``, ``type``, ``enabled``, ``node``) and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nodes = cmds.ls(type="aiAOV") or []
        aovs = []
        for node in nodes:
            try:
                aov_name = cmds.getAttr("{}.name".format(node))
                type_int = cmds.getAttr("{}.type".format(node))
                enabled = bool(cmds.getAttr("{}.enabled".format(node)))
                aovs.append(
                    {
                        "node": node,
                        "name": aov_name,
                        "type": _INT_TO_TYPE.get(type_int, "RGB"),
                        "enabled": enabled,
                    }
                )
            except Exception:
                pass

        return maya_success(
            "Found {} Arnold AOV(s)".format(len(aovs)),
            prompt="Use add_aov to create more passes or enable_aov to toggle individual AOVs.",
            aovs=aovs,
            count=len(aovs),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list AOVs")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_aovs`."""
    return list_aovs(**kwargs)


if __name__ == "__main__":
    import json

    result = list_aovs()
    print(json.dumps(result))
