"""Validate a Maya scene for render farm submission."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def validate_scene_for_farm() -> dict:
    """Check the open Maya scene for common farm-submission issues.

    Checks performed:
    - Scene is saved (not untitled)
    - No unresolved file texture paths
    - No unloaded references
    - Render frame range is set (startFrame < endFrame)
    - Active render layer exists

    Returns:
        ActionResultModel dict with ``context.issues`` list and ``context.valid`` flag.
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
            try:
                tex_path = cmds.getAttr("{}.fileTextureName".format(fn)) or ""
                if tex_path and not os.path.isfile(tex_path):
                    issues.append("Missing texture: '{}' on node '{}'".format(tex_path, fn))
            except Exception:
                pass

        # 3. Unloaded references
        refs = cmds.file(q=True, reference=True) or []
        for ref in refs:
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
            return maya_success(
                "Scene is valid for farm submission",
                prompt="Use write_render_job to create a job spec for the render farm.",
                valid=True,
                issues=[],
                scene_path=scene_path,
            )
        else:
            return maya_success(
                "Scene has {} issue(s) that should be resolved before submission".format(len(issues)),
                prompt="Fix the listed issues, then re-run validate_scene_for_farm.",
                valid=False,
                issues=issues,
                scene_path=scene_path,
            )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to validate scene")


def main(**kwargs):
    return validate_scene_for_farm(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(validate_scene_for_farm()))
