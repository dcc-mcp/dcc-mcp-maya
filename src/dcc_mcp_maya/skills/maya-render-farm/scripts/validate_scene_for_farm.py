"""Validate a Maya scene for render farm submission."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_core.cancellation import CancelledError
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.dispatcher import check_maya_cancelled


def validate_scene_for_farm() -> dict:
    """Check the open Maya scene for common farm-submission issues.

    Checks performed:
    - Scene is saved (not untitled)
    - No unresolved file texture paths
    - No unloaded references
    - Render frame range is set (startFrame < endFrame)
    - Active render layer exists

    Cooperative cancellation (issue #85):
        A scene with thousands of file nodes or references can take several
        seconds to validate.  We call :func:`check_maya_cancelled` between
        each node so an MCP ``notifications/cancelled`` or a dispatcher
        ``cancel(...)`` aborts the scan promptly instead of blocking the
        UI thread until every node is inspected.

    Returns:
        ToolResult dict with ``context.issues`` list and ``context.valid`` flag.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        issues = []  # type: List[str]

        # 1. Scene is saved
        scene_path = cmds.file(q=True, sceneName=True) or ""
        if not scene_path:
            issues.append("Scene is unsaved (untitled) — save before submitting")

        # 2. Missing file textures
        file_nodes = cmds.ls(type="file") or []
        for fn in file_nodes:
            # Cooperative cancellation checkpoint — cheap no-op outside
            # an MCP request, raises ``CancelledError`` when the owning
            # ``tools/call`` is cancelled or the dispatcher is shutting down.
            check_maya_cancelled()
            try:
                tex_path = cmds.getAttr("{}.fileTextureName".format(fn)) or ""
                if tex_path and not os.path.isfile(tex_path):
                    issues.append("Missing texture: '{}' on node '{}'".format(tex_path, fn))
            except Exception:
                pass

        # 3. Unloaded references
        refs = cmds.file(q=True, reference=True) or []
        for ref in refs:
            check_maya_cancelled()
            try:
                loaded = cmds.referenceQuery(ref, isLoaded=True)
                if not loaded:
                    issues.append("Unloaded reference: '{}'".format(ref))
            except Exception:
                pass

        # 4. Render frame range
        try:
            start = cmds.getAttr("defaultRenderGlobals.startFrame")
            end = cmds.getAttr("defaultRenderGlobals.endFrame")
            if end <= start:
                issues.append("Render frame range invalid: startFrame={} endFrame={}".format(start, end))
        except Exception:
            issues.append("Could not query defaultRenderGlobals frame range")

        # 5. Active render layer
        try:
            current_layer = cmds.editRenderLayerGlobals(q=True, currentRenderLayer=True)
            if not current_layer:
                issues.append("No active render layer found")
        except Exception:
            pass

        valid = len(issues) == 0
        if valid:
            return skill_success(
                "Scene is valid for farm submission",
                prompt="Use write_render_job to create a job spec for the render farm.",
                valid=True,
                issues=[],
                scene_path=scene_path,
            )
        else:
            return skill_success(
                "Scene has {} issue(s) that should be resolved before submission".format(len(issues)),
                prompt="Fix the listed issues, then re-run validate_scene_for_farm.",
                valid=False,
                issues=issues,
                scene_path=scene_path,
            )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except CancelledError:
        # Cooperative cancellation — propagate so the dispatcher can mark
        # the job as cancelled rather than reporting it as a generic
        # skill exception (issue #85).
        raise
    except Exception as exc:
        return skill_exception(exc, message="Failed to validate scene")


@skill_entry
def main(**kwargs):
    return validate_scene_for_farm(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
