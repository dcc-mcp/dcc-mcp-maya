"""Round 17: Tests for maya-skinning-utils, maya-rig-utils, maya-render-passes,
maya-pose-library, and maya-light-rig skills.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os
import sys
from unittest.mock import patch

# Import third-party modules
from tests.conftest import load_skill_script, make_mock_maya

# ---------------------------------------------------------------------------
# maya-skinning-utils
# ---------------------------------------------------------------------------


class TestCopySkinWeights:
    """Tests for copy_skin_weights script."""

    def test_copy_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.skinCluster.return_value = ["joint1", "joint2"]
        mock_cmds.copySkinWeights.return_value = None
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("sourceMesh", "targetMesh")
        assert result["success"] is True
        assert result["context"]["source_mesh"] == "sourceMesh"
        assert result["context"]["target_mesh"] == "targetMesh"

    def test_source_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("missing_src", "targetMesh")
        assert result["success"] is False

    def test_no_skin_cluster_on_source(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = []
        mock_cmds.listHistory.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("sourceMesh", "targetMesh")
        assert result["success"] is False
        assert "skin cluster" in result["message"].lower()

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("src", "dst")
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.skinCluster.return_value = ["j1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.main(source_mesh="src", target_mesh="dst")
        assert isinstance(result, dict)


class TestNormalizeSkinWeights:
    """Tests for normalize_skin_weights script."""

    def test_normalize_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.normalize_skin_weights("pSphere1")
        assert result["success"] is True
        assert result["context"]["skin_cluster_name"] == "skinCluster1"

    def test_mesh_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.normalize_skin_weights("missing")
        assert result["success"] is False

    def test_no_skin_cluster(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = []
        mock_cmds.listHistory.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.normalize_skin_weights("pSphere1")
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.normalize_skin_weights("pSphere1")
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.main(mesh="pSphere1")
        assert result["success"] is True


class TestMirrorSkinWeights:
    """Tests for mirror_skin_weights script."""

    def test_mirror_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("pSphere1", mirror_mode="YZ")
        assert result["success"] is True
        assert result["context"]["mirror_mode"] == "YZ"

    def test_mesh_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("missing")
        assert result["success"] is False

    def test_no_skin_cluster(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = []
        mock_cmds.listHistory.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("pSphere1")
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("pSphere1")
        assert result["success"] is False

    def test_negative_to_positive(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("pSphere1", positive_to_negative=False)
        assert result["success"] is True
        assert result["context"]["positive_to_negative"] is False


class TestPruneSkinWeights:
    """Tests for prune_skin_weights script."""

    def test_prune_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.prune_skin_weights("pSphere1", prune_value=0.05)
        assert result["success"] is True
        assert result["context"]["prune_value"] == 0.05

    def test_mesh_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.prune_skin_weights("missing")
        assert result["success"] is False

    def test_no_skin_cluster(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = []
        mock_cmds.listHistory.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.prune_skin_weights("pSphere1")
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.prune_skin_weights("pSphere1")
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["skinCluster1"]
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.main(mesh="pSphere1", prune_value=0.01)
        assert result["success"] is True


# ---------------------------------------------------------------------------
# maya-rig-utils
# ---------------------------------------------------------------------------


class TestCreateControlCurve:
    """Tests for create_control_curve script."""

    def test_create_circle(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.curve.return_value = "ctrl_root"
        mock_cmds.listRelatives.return_value = ["ctrl_rootShape"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "create_control_curve")
            result = mod.create_control_curve(shape="circle", name="ctrl_root")
        assert result["success"] is True
        assert result["context"]["curve_name"] == "ctrl_root"
        assert result["context"]["shape"] == "circle"

    def test_create_with_color(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.curve.return_value = "ctrl_color"
        mock_cmds.listRelatives.return_value = ["ctrl_colorShape"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "create_control_curve")
            result = mod.create_control_curve(shape="square", color=17)
        assert result["success"] is True
        assert result["context"]["color"] == 17

    def test_unknown_shape(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "create_control_curve")
            result = mod.create_control_curve(shape="unknown_shape")
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-rig-utils", "create_control_curve")
            result = mod.create_control_curve()
        assert result["success"] is False

    def test_all_preset_shapes(self):
        for shape in ("circle", "square", "triangle", "arrow", "diamond"):
            mock_maya, mock_cmds = make_mock_maya()
            mock_cmds.curve.return_value = "{}_ctrl".format(shape)
            mock_cmds.listRelatives.return_value = ["{}_ctrlShape".format(shape)]
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-rig-utils", "create_control_curve")
                result = mod.create_control_curve(shape=shape)
            assert result["success"] is True, "Shape '{}' failed".format(shape)

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.curve.return_value = "circle_ctrl"
        mock_cmds.listRelatives.return_value = ["circle_ctrlShape"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "create_control_curve")
            result = mod.main(shape="circle")
        assert result["success"] is True


class TestLockHideAttributes:
    """Tests for lock_hide_attributes script."""

    def test_lock_and_hide(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "lock_hide_attributes")
            result = mod.lock_hide_attributes("ctrl_root", attributes=["sx", "sy", "sz"])
        assert result["success"] is True
        assert result["context"]["lock"] is True
        assert result["context"]["hide"] is True

    def test_node_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "lock_hide_attributes")
            result = mod.lock_hide_attributes("missing_node")
        assert result["success"] is False

    def test_skip_missing_attribute(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "lock_hide_attributes")
            result = mod.lock_hide_attributes("ctrl", attributes=["nonexistent"])
        assert result["success"] is True
        assert result["context"]["processed_attributes"] == []

    def test_lock_only(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "lock_hide_attributes")
            result = mod.lock_hide_attributes("ctrl", attributes=["tx"], lock=True, hide=False)
        assert result["success"] is True

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-rig-utils", "lock_hide_attributes")
            result = mod.lock_hide_attributes("ctrl")
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "lock_hide_attributes")
            result = mod.main(node="ctrl", attributes=["v"])
        assert result["success"] is True


class TestAddSpaceSwitch:
    """Tests for add_space_switch script."""

    def test_add_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = False
        mock_cmds.parentConstraint.side_effect = [
            ["pConst1"],
            ["world_W0", "hip_W1"],
        ]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "add_space_switch")
            result = mod.add_space_switch(
                "hand_ctrl",
                ["world_loc", "hip_ctrl"],
                ["world", "hip"],
            )
        assert result["success"] is True
        assert result["context"]["constraint_node"] == "pConst1"

    def test_control_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n != "hand_ctrl"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "add_space_switch")
            result = mod.add_space_switch("hand_ctrl", ["world_loc"], ["world"])
        assert result["success"] is False

    def test_mismatched_lengths(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "add_space_switch")
            result = mod.add_space_switch("ctrl", ["s1", "s2"], ["name1"])
        assert result["success"] is False
        assert "length" in result["message"].lower()

    def test_missing_driver(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n not in ["missing_loc"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "add_space_switch")
            result = mod.add_space_switch("ctrl", ["missing_loc"], ["world"])
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-rig-utils", "add_space_switch")
            result = mod.add_space_switch("ctrl", ["s1"], ["world"])
        assert result["success"] is False


class TestConnectAttributes:
    """Tests for connect_attributes script."""

    def test_connect_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.connectionInfo.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "connect_attributes")
            result = mod.connect_attributes([["src.tx", "dst.tx"]])
        assert result["success"] is True
        assert result["context"]["connected_count"] == 1

    def test_empty_connections(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "connect_attributes")
            result = mod.connect_attributes([])
        assert result["success"] is False

    def test_invalid_pair_format(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "connect_attributes")
            result = mod.connect_attributes([["single_item"]])
        # All pairs failed → error_result; message mentions failure
        assert result["success"] is False

    def test_connection_exception(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.connectionInfo.return_value = False
        mock_cmds.connectAttr.side_effect = RuntimeError("already connected")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "connect_attributes")
            result = mod.connect_attributes([["src.tx", "dst.tx"]])
        # All pairs failed → error_result
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-rig-utils", "connect_attributes")
            result = mod.connect_attributes([["a.tx", "b.tx"]])
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.connectionInfo.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-rig-utils", "connect_attributes")
            result = mod.main(connections=[["a.tx", "b.tx"]])
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-render-passes
# ---------------------------------------------------------------------------


class TestCreateRenderPass:
    """Tests for create_render_pass script."""

    def test_create_maya_software(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.createNode.return_value = "beauty_pass"
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "create_render_pass")
            result = mod.create_render_pass(pass_type="beauty", name="beauty_pass")
        assert result["success"] is True
        assert result["context"]["pass_node"] == "beauty_pass"

    def test_create_arnold_aov(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.createNode.return_value = "diffuse_aov"
        mock_cmds.pluginInfo.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "create_render_pass")
            result = mod.create_render_pass(pass_type="diffuse", renderer="arnold")
        assert result["success"] is True
        assert result["context"]["renderer"] == "arnold"

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-render-passes", "create_render_pass")
            result = mod.create_render_pass()
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.createNode.return_value = "shadow_pass"
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "create_render_pass")
            result = mod.main(pass_type="shadow")
        assert result["success"] is True


class TestListRenderPasses:
    """Tests for list_render_passes script."""

    def test_list_empty(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "list_render_passes")
            result = mod.list_render_passes()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_with_nodes(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.side_effect = lambda type=None: (
            ["beauty_pass"] if type == "renderPass" else ["diffuse_aov"] if type == "aiAOV" else []
        )
        mock_cmds.objectType.return_value = "renderPass"
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "list_render_passes")
            result = mod.list_render_passes()
        assert result["success"] is True
        assert result["context"]["count"] >= 1

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-render-passes", "list_render_passes")
            result = mod.list_render_passes()
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "list_render_passes")
            result = mod.main()
        assert isinstance(result, dict)


class TestEnableRenderPass:
    """Tests for enable_render_pass script."""

    def test_enable_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "enable_render_pass")
            result = mod.enable_render_pass("beauty_pass", enabled=True)
        assert result["success"] is True
        assert result["context"]["enabled"] is True

    def test_disable_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "enable_render_pass")
            result = mod.enable_render_pass("beauty_pass", enabled=False)
        assert result["success"] is True
        assert result["context"]["enabled"] is False

    def test_pass_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "enable_render_pass")
            result = mod.enable_render_pass("missing_pass")
        assert result["success"] is False

    def test_no_toggle_attr(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "enable_render_pass")
            result = mod.enable_render_pass("strange_pass")
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-render-passes", "enable_render_pass")
            result = mod.enable_render_pass("some_pass")
        assert result["success"] is False


class TestSetRenderPassOutput:
    """Tests for set_render_pass_output script."""

    def test_set_output_path(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.side_effect = lambda attr, node, exists: attr == "fileNamePrefix"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "set_render_pass_output")
            result = mod.set_render_pass_output("beauty_pass", output_path="images/beauty")
        assert result["success"] is True
        assert result["context"]["output_path"] == "images/beauty"

    def test_pass_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "set_render_pass_output")
            result = mod.set_render_pass_output("missing")
        assert result["success"] is False

    def test_no_settable_attrs(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-passes", "set_render_pass_output")
            result = mod.set_render_pass_output("some_pass", output_path="images/x")
        assert result["success"] is True

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-render-passes", "set_render_pass_output")
            result = mod.set_render_pass_output("p", output_path="x", image_format="exr")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-pose-library
# ---------------------------------------------------------------------------


class TestSavePose:
    """Tests for save_pose script."""

    def test_save_success(self, tmp_path):
        pose_file = str(tmp_path / "test.json")
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["ctrl_a"]
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 1.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "save_pose")
            result = mod.save_pose(pose_file, controls=["ctrl_a"])
        assert result["success"] is True
        assert os.path.isfile(pose_file)

    def test_no_controls(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "save_pose")
            result = mod.save_pose("/tmp/pose.json")
        assert result["success"] is False

    def test_no_overwrite(self, tmp_path):
        pose_file = str(tmp_path / "existing.json")
        with open(pose_file, "w") as f:
            f.write("{}")
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "save_pose")
            result = mod.save_pose(pose_file, controls=["ctrl"], overwrite=False)
        assert result["success"] is False
        assert "already exists" in result["message"]

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-pose-library", "save_pose")
            result = mod.save_pose("/tmp/pose.json", controls=["ctrl"])
        assert result["success"] is False

    def test_main_passthrough(self, tmp_path):
        pose_file = str(tmp_path / "main_test.json")
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["ctrl"]
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 0.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "save_pose")
            result = mod.main(file_path=pose_file, controls=["ctrl"])
        assert result["success"] is True


class TestLoadPose:
    """Tests for load_pose script."""

    def test_load_success(self, tmp_path):
        pose_file = str(tmp_path / "test.json")
        pose_data = {"ctrl_a": {"tx": 1.0, "ty": 2.0}}
        with open(pose_file, "w") as f:
            json.dump(pose_data, f)
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "load_pose")
            result = mod.load_pose(pose_file)
        assert result["success"] is True
        assert result["context"]["applied_count"] == 1

    def test_file_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "load_pose")
            result = mod.load_pose("/nonexistent/pose.json")
        assert result["success"] is False

    def test_skip_missing_controls(self, tmp_path):
        pose_file = str(tmp_path / "missing.json")
        with open(pose_file, "w") as f:
            json.dump({"missing_ctrl": {"tx": 0.0}}, f)
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "load_pose")
            result = mod.load_pose(pose_file, skip_missing=True)
        assert result["success"] is True
        assert "missing_ctrl" in result["context"]["missing_controls"]

    def test_error_on_missing(self, tmp_path):
        pose_file = str(tmp_path / "strict.json")
        with open(pose_file, "w") as f:
            json.dump({"gone_ctrl": {"tx": 0.0}}, f)
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "load_pose")
            result = mod.load_pose(pose_file, skip_missing=False)
        assert result["success"] is False

    def test_no_maya(self, tmp_path):
        pose_file = str(tmp_path / "noma.json")
        with open(pose_file, "w") as f:
            json.dump({"ctrl": {"tx": 0.0}}, f)
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-pose-library", "load_pose")
            result = mod.load_pose(pose_file)
        assert result["success"] is False


class TestListPoses:
    """Tests for list_poses script."""

    def test_list_success(self, tmp_path):
        for i in range(3):
            pose_data = {"ctrl_{}".format(i): {"tx": float(i)}}
            with open(str(tmp_path / "pose_{}.json".format(i)), "w") as f:
                json.dump(pose_data, f)
        mod = load_skill_script("maya-pose-library", "list_poses")
        result = mod.list_poses(str(tmp_path))
        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_directory_not_found(self):
        mod = load_skill_script("maya-pose-library", "list_poses")
        result = mod.list_poses("/nonexistent/dir")
        assert result["success"] is False

    def test_empty_directory(self, tmp_path):
        mod = load_skill_script("maya-pose-library", "list_poses")
        result = mod.list_poses(str(tmp_path))
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        with open(str(sub / "pose.json"), "w") as f:
            json.dump({}, f)
        mod = load_skill_script("maya-pose-library", "list_poses")
        result_shallow = mod.list_poses(str(tmp_path), recursive=False)
        result_deep = mod.list_poses(str(tmp_path), recursive=True)
        assert result_shallow["context"]["count"] == 0
        assert result_deep["context"]["count"] == 1

    def test_main_passthrough(self, tmp_path):
        mod = load_skill_script("maya-pose-library", "list_poses")
        result = mod.main(directory=str(tmp_path))
        assert isinstance(result, dict)


class TestMirrorPose:
    """Tests for mirror_pose script."""

    def test_mirror_to_file(self, tmp_path):
        src = str(tmp_path / "src.json")
        dst = str(tmp_path / "dst.json")
        pose = {
            "L_hand": {"tx": 1.0, "ty": 2.0, "tz": 0.0},
            "R_hand": {"tx": -1.0, "ty": 2.0, "tz": 0.0},
        }
        with open(src, "w") as f:
            json.dump(pose, f)
        mod = load_skill_script("maya-pose-library", "mirror_pose")
        result = mod.mirror_pose(src, output_path=dst)
        assert result["success"] is True
        assert os.path.isfile(dst)

    def test_file_not_found(self):
        mod = load_skill_script("maya-pose-library", "mirror_pose")
        result = mod.mirror_pose("/nonexistent.json")
        assert result["success"] is False

    def test_mirror_apply_to_scene(self, tmp_path):
        src = str(tmp_path / "scene.json")
        pose = {"L_arm": {"tx": 5.0, "ry": 30.0}}
        with open(src, "w") as f:
            json.dump(pose, f)
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-pose-library", "mirror_pose")
            result = mod.mirror_pose(src, output_path=None)
        assert result["success"] is True

    def test_main_passthrough(self, tmp_path):
        src = str(tmp_path / "main.json")
        dst = str(tmp_path / "main_mirror.json")
        with open(src, "w") as f:
            json.dump({"ctrl": {"tx": 1.0}}, f)
        mod = load_skill_script("maya-pose-library", "mirror_pose")
        result = mod.main(file_path=src, output_path=dst)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-light-rig
# ---------------------------------------------------------------------------


class TestCreateThreePointRig:
    """Tests for create_three_point_rig script."""

    def test_create_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.group.return_value = "threePoint_rig"
        mock_cmds.createNode.side_effect = [
            "threePoint_rig_key",
            "threePoint_rig_keyShape",
            "threePoint_rig_fill",
            "threePoint_rig_fillShape",
            "threePoint_rig_rim",
            "threePoint_rig_rimShape",
        ]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "create_three_point_rig")
            result = mod.create_three_point_rig(name="threePoint_rig")
        assert result["success"] is True
        assert result["context"]["rig_group"] == "threePoint_rig"

    def test_custom_intensities(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.group.return_value = "hero_rig"
        mock_cmds.createNode.side_effect = ["k", "kS", "f", "fS", "r", "rS"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "create_three_point_rig")
            result = mod.create_three_point_rig(
                name="hero_rig",
                key_intensity=2.0,
                fill_intensity=0.3,
                rim_intensity=1.5,
            )
        assert result["success"] is True

    def test_spot_light_type(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.group.return_value = "spot_rig"
        mock_cmds.createNode.side_effect = ["k", "kS", "f", "fS", "r", "rS"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "create_three_point_rig")
            result = mod.create_three_point_rig(light_type="spotLight")
        assert result["success"] is True
        assert result["context"]["light_type"] == "spotLight"

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-light-rig", "create_three_point_rig")
            result = mod.create_three_point_rig()
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.group.return_value = "rig"
        mock_cmds.createNode.side_effect = ["k", "kS", "f", "fS", "r", "rS"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "create_three_point_rig")
            result = mod.main()
        assert isinstance(result, dict)


class TestCreateHdriDome:
    """Tests for create_hdri_dome script."""

    def test_create_arnold(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.createNode.side_effect = ["env_dome", "env_dome_Shape", "env_dome_texture"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "create_hdri_dome")
            result = mod.create_hdri_dome("/path/env.hdr", name="env_dome")
        assert result["success"] is True
        assert result["context"]["hdri_path"] == "/path/env.hdr"

    def test_create_fallback(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.pluginInfo.return_value = False
        mock_cmds.createNode.side_effect = ["dome_t", "dome_s", "dome_file"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "create_hdri_dome")
            result = mod.create_hdri_dome("/path/env.exr")
        assert result["success"] is True

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-light-rig", "create_hdri_dome")
            result = mod.create_hdri_dome("/path/env.hdr")
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.pluginInfo.return_value = False
        mock_cmds.createNode.side_effect = ["t", "s", "f"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "create_hdri_dome")
            result = mod.main(hdri_path="/p/env.hdr")
        assert isinstance(result, dict)


class TestListLightRigs:
    """Tests for list_light_rigs script."""

    def test_list_empty(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "list_light_rigs")
            result = mod.list_light_rigs()
        assert result["success"] is True
        assert result["context"]["total_lights"] == 0

    def test_list_with_lights(self):
        mock_maya, mock_cmds = make_mock_maya()

        def _ls_side(type=None):
            if type == "directionalLight":
                return ["dirLight1Shape"]
            return []

        mock_cmds.ls.side_effect = _ls_side
        mock_cmds.listRelatives.side_effect = [
            ["dirLight1"],
            ["threePoint_rig"],
        ]
        mock_cmds.objectType.return_value = "directionalLight"
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 1.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "list_light_rigs")
            result = mod.list_light_rigs()
        assert result["success"] is True
        assert result["context"]["total_lights"] >= 1

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-light-rig", "list_light_rigs")
            result = mod.list_light_rigs()
        assert result["success"] is False


class TestSetLightRigIntensity:
    """Tests for set_light_rig_intensity script."""

    def test_set_absolute(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "directionalLight"
        mock_cmds.listRelatives.return_value = ["lightShape1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "set_light_rig_intensity")
            result = mod.set_light_rig_intensity("threePoint_rig", intensity=2.0)
        assert result["success"] is True

    def test_multiply(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "directionalLight"
        mock_cmds.listRelatives.return_value = ["lightShape1"]
        mock_cmds.getAttr.return_value = 1.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "set_light_rig_intensity")
            result = mod.set_light_rig_intensity("rig", intensity=1.5, multiply=True)
        assert result["success"] is True

    def test_rig_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "set_light_rig_intensity")
            result = mod.set_light_rig_intensity("missing_rig", intensity=1.0)
        assert result["success"] is False

    def test_no_lights_in_group(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "set_light_rig_intensity")
            result = mod.set_light_rig_intensity("empty_rig", intensity=1.0)
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-light-rig", "set_light_rig_intensity")
            result = mod.set_light_rig_intensity("rig", intensity=1.0)
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "directionalLight"
        mock_cmds.listRelatives.return_value = ["ls1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-light-rig", "set_light_rig_intensity")
            result = mod.main(rig_group="rig", intensity=1.0)
        assert isinstance(result, dict)
