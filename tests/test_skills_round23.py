"""Round 23 tests: maya-proxy-mesh (update_proxy), maya-color-grading, maya-rig-utils, maya-shot-export."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def load_script(skill_dir: str, script_name: str):
    """Dynamically load a skill script, injecting a mock Maya environment."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.api"] = MagicMock()
    sys.modules["maya.utils"] = MagicMock()

    script_path = SKILLS_ROOT / skill_dir / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name[:-3], str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for key in ["maya", "maya.cmds", "maya.api", "maya.utils"]:
        sys.modules.pop(key, None)

    return mod, mock_cmds


# ---------------------------------------------------------------------------
# maya-proxy-mesh: update_proxy
# ---------------------------------------------------------------------------


class TestUpdateProxy:
    def test_missing_proxy_param(self):
        mod, _ = load_script("maya-proxy-mesh", "update_proxy.py")
        r = mod.run({})
        assert not r.success
        assert "'proxy' is required" in r.error

    def test_invalid_method(self):
        mod, _ = load_script("maya-proxy-mesh", "update_proxy.py")
        r = mod.run({"proxy": "myCube_proxy", "method": "invalid"})
        assert not r.success
        assert "method must be" in r.error

    def test_proxy_not_found(self):
        mod, cmds = load_script("maya-proxy-mesh", "update_proxy.py")
        cmds.objExists.return_value = False
        r = mod.run({"proxy": "missing_proxy"})
        assert not r.success
        assert "Proxy not found" in r.message

    def test_no_lod_attribute(self):
        mod, cmds = load_script("maya-proxy-mesh", "update_proxy.py")
        cmds.objExists.return_value = True
        cmds.attributeQuery.return_value = False
        r = mod.run({"proxy": "badNode"})
        assert not r.success
        assert "Not a proxy" in r.message

    def test_lod_level_not_zero(self):
        mod, cmds = load_script("maya-proxy-mesh", "update_proxy.py")
        cmds.objExists.return_value = True
        cmds.attributeQuery.return_value = True
        cmds.getAttr.return_value = 1  # source, not proxy
        r = mod.run({"proxy": "highRes"})
        assert not r.success
        assert "lod_level != 0" in r.error

    def test_source_not_found_among_siblings(self):
        mod, cmds = load_script("maya-proxy-mesh", "update_proxy.py")
        cmds.objExists.return_value = True

        def attr_query_side_effect(*args, **kwargs):
            if kwargs.get("exists"):
                return True
            return None

        cmds.attributeQuery.side_effect = attr_query_side_effect

        def get_attr_side_effect(attr, **kwargs):
            if "lod_level" in attr:
                return 0  # it's a proxy
            return 0

        cmds.getAttr.side_effect = get_attr_side_effect
        cmds.listRelatives.return_value = []  # no parent → no siblings
        r = mod.run({"proxy": "orphan_proxy"})
        assert not r.success
        assert "Source not found" in r.message

    def test_successful_bbox_update(self):
        mod, cmds = load_script("maya-proxy-mesh", "update_proxy.py")
        cmds.objExists.return_value = True

        call_count = [0]

        def attr_query_side_effect(*args, **kwargs):
            if kwargs.get("exists"):
                return True
            return None

        cmds.attributeQuery.side_effect = attr_query_side_effect

        def get_attr_side_effect(attr, **kwargs):
            if "lod_level" in attr:
                if call_count[0] == 0:
                    call_count[0] += 1
                    return 0  # first call: proxy
                return 1  # sibling: source
            return 0

        cmds.getAttr.side_effect = get_attr_side_effect
        cmds.listRelatives.side_effect = [
            ["parentGrp"],           # parent of proxy
            ["parentGrp_sib", "orphan_proxy"],  # children of parent
        ]
        cmds.exactWorldBoundingBox.return_value = [-1, -1, -1, 1, 1, 1]
        cmds.polyCube.return_value = [("orphan_proxy", "polyCubeShape")]
        r = mod.run({"proxy": "orphan_proxy", "method": "bbox"})
        assert r.success
        assert "Updated proxy" in r.message

    def test_exception_handling(self):
        mod, cmds = load_script("maya-proxy-mesh", "update_proxy.py")
        cmds.objExists.side_effect = RuntimeError("Maya crash")
        r = mod.run({"proxy": "bad"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-color-grading: set_viewport_gamma
# ---------------------------------------------------------------------------


class TestSetViewportGamma:
    def test_success(self):
        mod, cmds = load_script("maya-color-grading", "set_viewport_gamma.py")
        cmds.modelPanel.return_value = True
        r = mod.run({"panel": "modelPanel1", "gamma": 2.4})
        assert r.success
        assert "2.4" in r.message

    def test_default_panel(self):
        mod, cmds = load_script("maya-color-grading", "set_viewport_gamma.py")
        cmds.modelPanel.return_value = True
        r = mod.run({"gamma": 1.0})
        assert r.success
        assert r.context["panel"] == "modelPanel4"

    def test_invalid_gamma_type(self):
        mod, _ = load_script("maya-color-grading", "set_viewport_gamma.py")
        r = mod.run({"gamma": "bad"})
        assert not r.success
        assert "'gamma' must be a number" in r.error

    def test_negative_gamma(self):
        mod, _ = load_script("maya-color-grading", "set_viewport_gamma.py")
        r = mod.run({"gamma": -1.0})
        assert not r.success
        assert "must be > 0" in r.error

    def test_panel_not_found(self):
        mod, cmds = load_script("maya-color-grading", "set_viewport_gamma.py")
        cmds.modelPanel.return_value = False
        r = mod.run({"panel": "noPanel", "gamma": 2.2})
        assert not r.success
        assert "Panel not found" in r.message

    def test_exception(self):
        mod, cmds = load_script("maya-color-grading", "set_viewport_gamma.py")
        cmds.modelPanel.side_effect = RuntimeError("err")
        r = mod.run({"gamma": 1.0})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-color-grading: set_viewport_exposure
# ---------------------------------------------------------------------------


class TestSetViewportExposure:
    def test_success(self):
        mod, cmds = load_script("maya-color-grading", "set_viewport_exposure.py")
        cmds.modelPanel.return_value = True
        r = mod.run({"panel": "modelPanel1", "exposure": 1.5})
        assert r.success
        assert "1.5" in r.message

    def test_invalid_exposure(self):
        mod, _ = load_script("maya-color-grading", "set_viewport_exposure.py")
        r = mod.run({"exposure": "bad"})
        assert not r.success
        assert "'exposure' must be a number" in r.error

    def test_panel_not_found(self):
        mod, cmds = load_script("maya-color-grading", "set_viewport_exposure.py")
        cmds.modelPanel.return_value = False
        r = mod.run({"panel": "noPanel"})
        assert not r.success

    def test_exception(self):
        mod, cmds = load_script("maya-color-grading", "set_viewport_exposure.py")
        cmds.modelPanel.side_effect = RuntimeError("err")
        r = mod.run({})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-color-grading: set_color_transform
# ---------------------------------------------------------------------------


class TestSetColorTransform:
    def test_success(self):
        mod, cmds = load_script("maya-color-grading", "set_color_transform.py")
        cmds.modelPanel.return_value = True
        r = mod.run({"transform": "sRGB gamma"})
        assert r.success
        assert "sRGB gamma" in r.message

    def test_missing_transform(self):
        mod, _ = load_script("maya-color-grading", "set_color_transform.py")
        r = mod.run({})
        assert not r.success
        assert "'transform' is required" in r.error

    def test_panel_not_found(self):
        mod, cmds = load_script("maya-color-grading", "set_color_transform.py")
        cmds.modelPanel.return_value = False
        r = mod.run({"panel": "noPanel", "transform": "Raw"})
        assert not r.success

    def test_exception(self):
        mod, cmds = load_script("maya-color-grading", "set_color_transform.py")
        cmds.modelPanel.side_effect = RuntimeError("err")
        r = mod.run({"transform": "Linear"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-color-grading: list_color_transforms
# ---------------------------------------------------------------------------


class TestListColorTransforms:
    def test_success(self):
        mod, cmds = load_script("maya-color-grading", "list_color_transforms.py")
        cmds.colorManagementPrefs.side_effect = [
            ["sRGB", "Linear"],   # renderingSpaceNames
            ["sRGB gamma", "Raw"],  # viewTransformNames
        ]
        r = mod.run({})
        assert r.success
        assert r.context["count"] == 4

    def test_no_transforms(self):
        mod, cmds = load_script("maya-color-grading", "list_color_transforms.py")
        cmds.colorManagementPrefs.side_effect = [[], []]
        r = mod.run({})
        assert r.success
        assert r.context["count"] == 0

    def test_view_transforms_error_graceful(self):
        mod, cmds = load_script("maya-color-grading", "list_color_transforms.py")

        def side_effect(*args, **kwargs):
            if kwargs.get("renderingSpaceNames"):
                return ["sRGB"]
            raise RuntimeError("no view transforms")

        cmds.colorManagementPrefs.side_effect = side_effect
        r = mod.run({})
        assert r.success
        assert r.context["count"] == 1

    def test_exception(self):
        mod, cmds = load_script("maya-color-grading", "list_color_transforms.py")
        cmds.colorManagementPrefs.side_effect = RuntimeError("fail")
        r = mod.run({})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-color-grading: get_viewport_color_settings
# ---------------------------------------------------------------------------


class TestGetViewportColorSettings:
    def test_success(self):
        mod, cmds = load_script("maya-color-grading", "get_viewport_color_settings.py")
        cmds.modelPanel.return_value = True

        def editor_side_effect(*args, **kwargs):
            if kwargs.get("gamma"):
                return 2.2
            if kwargs.get("exposure"):
                return 0.5
            if kwargs.get("colorTransform"):
                return "sRGB gamma"
            return None

        cmds.modelEditor.side_effect = editor_side_effect
        r = mod.run({"panel": "modelPanel4"})
        assert r.success
        assert r.context["gamma"] == 2.2
        assert r.context["exposure"] == 0.5

    def test_panel_not_found(self):
        mod, cmds = load_script("maya-color-grading", "get_viewport_color_settings.py")
        cmds.modelPanel.return_value = False
        r = mod.run({"panel": "noPanel"})
        assert not r.success

    def test_color_transform_unavailable(self):
        mod, cmds = load_script("maya-color-grading", "get_viewport_color_settings.py")
        cmds.modelPanel.return_value = True

        def editor_side_effect(*args, **kwargs):
            if kwargs.get("gamma"):
                return 2.2
            if kwargs.get("exposure"):
                return 0.0
            if kwargs.get("colorTransform"):
                raise RuntimeError("no OCIO")
            return None

        cmds.modelEditor.side_effect = editor_side_effect
        r = mod.run({})
        assert r.success
        assert r.context["color_transform"] is None

    def test_exception(self):
        mod, cmds = load_script("maya-color-grading", "get_viewport_color_settings.py")
        cmds.modelPanel.side_effect = RuntimeError("crash")
        r = mod.run({})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-rig-utils: create_control_curve
# ---------------------------------------------------------------------------


class TestCreateControlCurve:
    def test_circle_default(self):
        mod, cmds = load_script("maya-rig-utils", "create_control_curve.py")
        cmds.circle.return_value = [("ctrl", "makeNurbCircle")]
        cmds.listRelatives.return_value = ["ctrlShape"]
        r = mod.run({"name": "ctrl", "shape": "circle"})
        assert r.success
        assert "circle" in r.message

    def test_square_shape(self):
        mod, cmds = load_script("maya-rig-utils", "create_control_curve.py")
        cmds.curve.return_value = "squareCtrl"
        cmds.listRelatives.return_value = ["squareCtrlShape"]
        r = mod.run({"name": "squareCtrl", "shape": "square"})
        assert r.success

    def test_invalid_shape(self):
        mod, _ = load_script("maya-rig-utils", "create_control_curve.py")
        r = mod.run({"shape": "triangle"})
        assert not r.success
        assert "shape must be one of" in r.error

    def test_color_applied(self):
        mod, cmds = load_script("maya-rig-utils", "create_control_curve.py")
        cmds.circle.return_value = [("ctrl", "makeNurbCircle")]
        cmds.listRelatives.return_value = ["ctrlShape"]
        r = mod.run({"name": "ctrl", "shape": "circle", "color": 13})
        assert r.success
        assert r.context["color"] == 13

    def test_scale_applied(self):
        mod, cmds = load_script("maya-rig-utils", "create_control_curve.py")
        cmds.circle.return_value = [("ctrl", "makeNurbCircle")]
        cmds.listRelatives.return_value = ["ctrlShape"]
        r = mod.run({"name": "ctrl", "shape": "circle", "scale": 2.0})
        assert r.success
        cmds.scale.assert_called_once()

    def test_exception(self):
        mod, cmds = load_script("maya-rig-utils", "create_control_curve.py")
        cmds.circle.side_effect = RuntimeError("no circle")
        r = mod.run({"name": "ctrl", "shape": "circle"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-rig-utils: add_offset_group
# ---------------------------------------------------------------------------


class TestAddOffsetGroup:
    def test_success_no_parent(self):
        mod, cmds = load_script("maya-rig-utils", "add_offset_group.py")
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = []
        cmds.group.return_value = "arm_ctrl_offset"
        cmds.parentConstraint.return_value = ["pCon"]
        r = mod.run({"control": "arm_ctrl"})
        assert r.success
        assert "arm_ctrl_offset" in r.message

    def test_success_with_parent(self):
        mod, cmds = load_script("maya-rig-utils", "add_offset_group.py")
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = ["parentGrp"]
        cmds.group.return_value = "arm_ctrl_offset"
        cmds.parentConstraint.return_value = ["pCon"]
        r = mod.run({"control": "arm_ctrl"})
        assert r.success

    def test_missing_control(self):
        mod, _ = load_script("maya-rig-utils", "add_offset_group.py")
        r = mod.run({})
        assert not r.success
        assert "'control' is required" in r.error

    def test_control_not_found(self):
        mod, cmds = load_script("maya-rig-utils", "add_offset_group.py")
        cmds.objExists.return_value = False
        r = mod.run({"control": "missing"})
        assert not r.success
        assert "Control not found" in r.message

    def test_custom_suffix(self):
        mod, cmds = load_script("maya-rig-utils", "add_offset_group.py")
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = []
        cmds.group.return_value = "arm_ctrl_zero"
        cmds.parentConstraint.return_value = ["pCon"]
        r = mod.run({"control": "arm_ctrl", "suffix": "_zero"})
        assert r.success

    def test_exception(self):
        mod, cmds = load_script("maya-rig-utils", "add_offset_group.py")
        cmds.objExists.side_effect = RuntimeError("crash")
        r = mod.run({"control": "ctrl"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-rig-utils: set_control_color
# ---------------------------------------------------------------------------


class TestSetControlColor:
    def test_success(self):
        mod, cmds = load_script("maya-rig-utils", "set_control_color.py")
        cmds.objExists.return_value = True
        cmds.listRelatives.side_effect = [["ctrlShape"], None]
        r = mod.run({"control": "myCtrl", "color": 17})
        assert r.success
        assert "17" in r.message

    def test_missing_control(self):
        mod, _ = load_script("maya-rig-utils", "set_control_color.py")
        r = mod.run({"color": 5})
        assert not r.success

    def test_invalid_color_type(self):
        mod, _ = load_script("maya-rig-utils", "set_control_color.py")
        r = mod.run({"control": "ctrl", "color": "red"})
        assert not r.success
        assert "'color' must be an integer" in r.error

    def test_out_of_range_color(self):
        mod, _ = load_script("maya-rig-utils", "set_control_color.py")
        r = mod.run({"control": "ctrl", "color": 50})
        assert not r.success
        assert "between 1 and 31" in r.error

    def test_no_shapes(self):
        mod, cmds = load_script("maya-rig-utils", "set_control_color.py")
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = []
        r = mod.run({"control": "myCtrl", "color": 5})
        assert not r.success
        assert "No shapes found" in r.message

    def test_exception(self):
        mod, cmds = load_script("maya-rig-utils", "set_control_color.py")
        cmds.objExists.side_effect = RuntimeError("crash")
        r = mod.run({"control": "ctrl", "color": 5})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-rig-utils: lock_control_attributes
# ---------------------------------------------------------------------------


class TestLockControlAttributes:
    def test_lock_defaults(self):
        mod, cmds = load_script("maya-rig-utils", "lock_control_attributes.py")
        cmds.objExists.return_value = True
        cmds.attributeQuery.return_value = True
        r = mod.run({"control": "myCtrl"})
        assert r.success
        assert "Locked" in r.message

    def test_unlock(self):
        mod, cmds = load_script("maya-rig-utils", "lock_control_attributes.py")
        cmds.objExists.return_value = True
        cmds.attributeQuery.return_value = True
        r = mod.run({"control": "myCtrl", "unlock": True})
        assert r.success
        assert "Unlocked" in r.message
        assert r.context["unlocked"] is True

    def test_missing_control(self):
        mod, _ = load_script("maya-rig-utils", "lock_control_attributes.py")
        r = mod.run({})
        assert not r.success

    def test_invalid_attributes_type(self):
        mod, _ = load_script("maya-rig-utils", "lock_control_attributes.py")
        r = mod.run({"control": "ctrl", "attributes": "tx"})
        assert not r.success
        assert "'attributes' must be a list" in r.error

    def test_control_not_found(self):
        mod, cmds = load_script("maya-rig-utils", "lock_control_attributes.py")
        cmds.objExists.return_value = False
        r = mod.run({"control": "missing"})
        assert not r.success

    def test_exception(self):
        mod, cmds = load_script("maya-rig-utils", "lock_control_attributes.py")
        cmds.objExists.side_effect = RuntimeError("err")
        r = mod.run({"control": "ctrl"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-rig-utils: mirror_control_curve
# ---------------------------------------------------------------------------


class TestMirrorControlCurve:
    def test_l_to_r_prefix(self):
        mod, cmds = load_script("maya-rig-utils", "mirror_control_curve.py")
        cmds.objExists.return_value = True
        cmds.duplicate.return_value = ["R_arm_ctrl"]
        cmds.listRelatives.side_effect = [
            ["L_arm_ctrlShape"],  # src shapes
            ["R_arm_ctrlShape"],  # dst shapes
        ]
        cmds.getAttr.return_value = False  # overrideEnabled
        r = mod.run({"control": "L_arm_ctrl"})
        assert r.success
        assert "R_arm_ctrl" in r.message

    def test_custom_target(self):
        mod, cmds = load_script("maya-rig-utils", "mirror_control_curve.py")
        cmds.objExists.return_value = True
        cmds.duplicate.return_value = ["custom_ctrl"]
        cmds.listRelatives.return_value = []
        r = mod.run({"control": "srcCtrl", "target": "custom_ctrl"})
        assert r.success
        assert r.context["mirrored"] == "custom_ctrl"

    def test_invalid_axis(self):
        mod, _ = load_script("maya-rig-utils", "mirror_control_curve.py")
        r = mod.run({"control": "ctrl", "axis": "w"})
        assert not r.success
        assert "axis must be" in r.error

    def test_missing_control(self):
        mod, _ = load_script("maya-rig-utils", "mirror_control_curve.py")
        r = mod.run({})
        assert not r.success

    def test_control_not_found(self):
        mod, cmds = load_script("maya-rig-utils", "mirror_control_curve.py")
        cmds.objExists.return_value = False
        r = mod.run({"control": "missing"})
        assert not r.success

    def test_exception(self):
        mod, cmds = load_script("maya-rig-utils", "mirror_control_curve.py")
        cmds.objExists.side_effect = RuntimeError("err")
        r = mod.run({"control": "ctrl"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-shot-export: export_shot_animation
# ---------------------------------------------------------------------------


class TestExportShotAnimation:
    def test_missing_shot(self):
        mod, _ = load_script("maya-shot-export", "export_shot_animation.py")
        r = mod.run({"output_path": "/tmp/out.fbx"})
        assert not r.success
        assert "'shot' is required" in r.error

    def test_missing_output(self):
        mod, _ = load_script("maya-shot-export", "export_shot_animation.py")
        r = mod.run({"shot": "shot001"})
        assert not r.success

    def test_invalid_format(self):
        mod, _ = load_script("maya-shot-export", "export_shot_animation.py")
        r = mod.run({"shot": "shot001", "output_path": "/tmp/out.abc", "format": "mp4"})
        assert not r.success
        assert "format must be" in r.error

    def test_shot_not_found(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_animation.py")
        cmds.objExists.return_value = False
        r = mod.run({"shot": "missing", "output_path": "/tmp/out.fbx"})
        assert not r.success

    def test_not_a_shot_node(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_animation.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "transform"
        r = mod.run({"shot": "notAShot", "output_path": "/tmp/out.fbx"})
        assert not r.success
        assert "Not a shot" in r.message

    def test_fbx_export_success(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_animation.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "shot"
        cmds.getAttr.side_effect = [1.0, 48.0]  # start, end
        cmds.ls.return_value = []

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "shot001.fbx")
            r = mod.run({"shot": "shot001", "output_path": out, "format": "fbx"})
        assert r.success
        assert "shot001" in r.message

    def test_exception(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_animation.py")
        cmds.objExists.side_effect = RuntimeError("crash")
        r = mod.run({"shot": "s", "output_path": "/tmp/out.fbx"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-shot-export: export_shot_camera
# ---------------------------------------------------------------------------


class TestExportShotCamera:
    def test_missing_shot(self):
        mod, _ = load_script("maya-shot-export", "export_shot_camera.py")
        r = mod.run({"output_path": "/tmp/cam.fbx"})
        assert not r.success

    def test_missing_output(self):
        mod, _ = load_script("maya-shot-export", "export_shot_camera.py")
        r = mod.run({"shot": "shot001"})
        assert not r.success

    def test_shot_not_found(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_camera.py")
        cmds.objExists.return_value = False
        r = mod.run({"shot": "missing", "output_path": "/tmp/cam.fbx"})
        assert not r.success

    def test_no_camera_assigned(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_camera.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "shot"
        cmds.getAttr.return_value = ""
        r = mod.run({"shot": "shot001", "output_path": "/tmp/cam.fbx"})
        assert not r.success
        assert "No camera assigned" in r.message

    def test_success_with_bake(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_camera.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "shot"
        cmds.getAttr.side_effect = ["persp", 1, 48]  # camera, start, end

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "cam.fbx")
            r = mod.run({"shot": "shot001", "output_path": out, "bake": True})
        assert r.success
        cmds.bakeResults.assert_called_once()

    def test_exception(self):
        mod, cmds = load_script("maya-shot-export", "export_shot_camera.py")
        cmds.objExists.side_effect = RuntimeError("crash")
        r = mod.run({"shot": "s", "output_path": "/tmp/cam.fbx"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-shot-export: playblast_shot
# ---------------------------------------------------------------------------


class TestPlayblastShot:
    def test_missing_shot(self):
        mod, _ = load_script("maya-shot-export", "playblast_shot.py")
        r = mod.run({"output_path": "/tmp/pb"})
        assert not r.success

    def test_missing_output(self):
        mod, _ = load_script("maya-shot-export", "playblast_shot.py")
        r = mod.run({"shot": "shot001"})
        assert not r.success

    def test_shot_not_found(self):
        mod, cmds = load_script("maya-shot-export", "playblast_shot.py")
        cmds.objExists.return_value = False
        r = mod.run({"shot": "missing", "output_path": "/tmp/pb"})
        assert not r.success

    def test_success(self):
        mod, cmds = load_script("maya-shot-export", "playblast_shot.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "shot"
        cmds.getAttr.side_effect = [1, 48]
        cmds.playblast.return_value = "/tmp/pb.mov"

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "shot001")
            r = mod.run({"shot": "shot001", "output_path": out})
        assert r.success
        assert r.context["start_frame"] == 1

    def test_prompt_present(self):
        mod, cmds = load_script("maya-shot-export", "playblast_shot.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "shot"
        cmds.getAttr.side_effect = [1, 24]
        cmds.playblast.return_value = "/tmp/s.mov"

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "shot")
            r = mod.run({"shot": "s1", "output_path": out})
        assert r.prompt

    def test_exception(self):
        mod, cmds = load_script("maya-shot-export", "playblast_shot.py")
        cmds.objExists.side_effect = RuntimeError("crash")
        r = mod.run({"shot": "s", "output_path": "/tmp/pb"})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-shot-export: list_shot_export_status
# ---------------------------------------------------------------------------


class TestListShotExportStatus:
    def test_no_shots(self):
        mod, cmds = load_script("maya-shot-export", "list_shot_export_status.py")
        cmds.ls.return_value = []
        r = mod.run({})
        assert r.success
        assert r.context["count"] == 0

    def test_shots_listed(self):
        mod, cmds = load_script("maya-shot-export", "list_shot_export_status.py")
        cmds.ls.return_value = ["shot001", "shot002"]

        def get_attr_side(attr, **kw):
            if "currentCamera" in attr:
                return "persp"
            if "startFrame" in attr:
                return 1
            if "endFrame" in attr:
                return 24
            if "shotEnabled" in attr:
                return True
            return None

        cmds.getAttr.side_effect = get_attr_side
        r = mod.run({})
        assert r.success
        assert r.context["count"] == 2

    def test_export_dir_check(self):
        mod, cmds = load_script("maya-shot-export", "list_shot_export_status.py")
        cmds.ls.return_value = ["shot001"]

        def get_attr_side(attr, **kw):
            if "currentCamera" in attr:
                return "persp"
            if "startFrame" in attr:
                return 1
            if "endFrame" in attr:
                return 24
            if "shotEnabled" in attr:
                return True
            return None

        cmds.getAttr.side_effect = get_attr_side

        with tempfile.TemporaryDirectory() as td:
            r = mod.run({"export_dir": td})
        assert r.success
        assert "exported" in r.context["shots"][0]

    def test_exception(self):
        mod, cmds = load_script("maya-shot-export", "list_shot_export_status.py")
        cmds.ls.side_effect = RuntimeError("crash")
        r = mod.run({})
        assert not r.success


# ---------------------------------------------------------------------------
# maya-shot-export: generate_export_manifest
# ---------------------------------------------------------------------------


class TestGenerateExportManifest:
    def test_missing_output(self):
        mod, _ = load_script("maya-shot-export", "generate_export_manifest.py")
        r = mod.run({})
        assert not r.success
        assert "'output_path' is required" in r.error

    def test_success_with_shots(self):
        mod, cmds = load_script("maya-shot-export", "generate_export_manifest.py")
        cmds.ls.return_value = ["shot001", "shot002"]

        def get_attr_side(attr, **kw):
            if "currentCamera" in attr:
                return "persp"
            if "startFrame" in attr:
                return 1
            if "endFrame" in attr:
                return 24
            if "shotEnabled" in attr:
                return True
            return None

        cmds.getAttr.side_effect = get_attr_side

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "manifest.json")
            r = mod.run({"output_path": out, "project": "TestProject"})

            assert r.success
            assert r.context["shot_count"] == 2
            # Verify JSON content
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            assert data["project"] == "TestProject"
            assert len(data["shots"]) == 2

    def test_no_shots(self):
        mod, cmds = load_script("maya-shot-export", "generate_export_manifest.py")
        cmds.ls.return_value = []

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "manifest.json")
            r = mod.run({"output_path": out})
        assert r.success
        assert r.context["shot_count"] == 0

    def test_exception(self):
        mod, cmds = load_script("maya-shot-export", "generate_export_manifest.py")
        cmds.ls.side_effect = RuntimeError("crash")

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "manifest.json")
            r = mod.run({"output_path": out})
        assert not r.success
