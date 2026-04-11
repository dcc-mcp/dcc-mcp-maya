"""Round 16: Tests for maya-blend-shape-utils, maya-xform-utils, maya-spline-ik,
maya-gpu-cache, and maya-instancer skills.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
from tests.conftest import load_skill_script, make_mock_maya

# ---------------------------------------------------------------------------
# maya-blend-shape-utils
# ---------------------------------------------------------------------------


class TestBlendShapeCreate:
    """Tests for create_blend_shape script."""

    def test_create_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.blendShape.return_value = ["blendShape1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "create_blend_shape")
            result = mod.create_blend_shape("pSphere1", ["pSphere2"])
        assert result["success"] is True
        assert result["context"]["blend_shape_node"] == "blendShape1"
        assert result["context"]["targets"] == ["pSphere2"]

    def test_missing_base_mesh(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "create_blend_shape")
            result = mod.create_blend_shape("missing_mesh", ["pSphere2"])
        assert result["success"] is False
        assert "missing_mesh" in result["message"]

    def test_missing_target(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        # base exists but target doesn't
        mock_cmds.objExists.side_effect = lambda n: n == "pSphere1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "create_blend_shape")
            result = mod.create_blend_shape("pSphere1", ["missing_target"])
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-blend-shape-utils", "create_blend_shape")
            result = mod.create_blend_shape("pSphere1", ["pSphere2"])
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.blendShape.return_value = ["blendShape1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "create_blend_shape")
            result = mod.main(base_mesh="pSphere1", targets=["pSphere2"])
        assert result["success"] is True


class TestBlendShapeList:
    """Tests for list_blend_shapes script."""

    def test_list_all(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["blendShape1"]
        mock_cmds.blendShape.side_effect = [
            [0.0, 0.5],  # weight query
            ["pSphere1"],  # geometry query
        ]
        mock_cmds.aliasAttr.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "list_blend_shapes")
            result = mod.list_blend_shapes()
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_list_for_mesh(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = ["blendShape1"]
        mock_cmds.blendShape.side_effect = [[1.0], ["pSphere1"]]
        mock_cmds.aliasAttr.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "list_blend_shapes")
            result = mod.list_blend_shapes(mesh="pSphere1")
        assert result["success"] is True

    def test_mesh_not_found(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "list_blend_shapes")
            result = mod.list_blend_shapes(mesh="missing")
        assert result["success"] is False

    def test_empty_scene(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "list_blend_shapes")
            result = mod.list_blend_shapes()
        assert result["success"] is True
        assert result["context"]["count"] == 0


class TestBlendShapeSetWeight:
    """Tests for set_blend_shape_weight script."""

    def test_set_by_index(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "set_blend_shape_weight")
            result = mod.set_blend_shape_weight("blendShape1", 0, 0.75)
        assert result["success"] is True
        assert result["context"]["weight"] == 0.75

    def test_set_by_name(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.aliasAttr.return_value = ["smile", "weight[0]"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "set_blend_shape_weight")
            result = mod.set_blend_shape_weight("blendShape1", "smile", 1.0)
        assert result["success"] is True
        assert result["context"]["target_index"] == 0

    def test_name_not_found(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.aliasAttr.return_value = ["other", "weight[1]"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "set_blend_shape_weight")
            result = mod.set_blend_shape_weight("blendShape1", "smile", 0.5)
        assert result["success"] is False

    def test_node_not_found(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "set_blend_shape_weight")
            result = mod.set_blend_shape_weight("missing", 0, 0.5)
        assert result["success"] is False


class TestBlendShapeGetWeights:
    """Tests for get_blend_shape_weights script."""

    def test_get_weights(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.blendShape.return_value = [0.0, 0.5, 1.0]
        mock_cmds.aliasAttr.return_value = ["smile", "weight[0]", "frown", "weight[1]"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "get_blend_shape_weights")
            result = mod.get_blend_shape_weights("blendShape1")
        assert result["success"] is True
        assert result["context"]["count"] == 3
        targets = result["context"]["targets"]
        assert targets[0]["name"] == "smile"
        assert targets[1]["name"] == "frown"

    def test_node_missing(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-blend-shape-utils", "get_blend_shape_weights")
            result = mod.get_blend_shape_weights("missing")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-xform-utils
# ---------------------------------------------------------------------------


class TestFreezeTransforms:
    """Tests for freeze_transforms script."""

    def test_freeze_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.return_value = [(0.0, 0.0, 0.0)]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "freeze_transforms")
            result = mod.freeze_transforms(["pSphere1"])
        assert result["success"] is True
        assert len(result["context"]["frozen_objects"]) == 1

    def test_no_objects(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "freeze_transforms")
            result = mod.freeze_transforms([])
        assert result["success"] is False

    def test_missing_objects(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "freeze_transforms")
            result = mod.freeze_transforms(["nonexistent"])
        assert result["success"] is False

    def test_dry_run(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.return_value = [(1.0, 2.0, 3.0)]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "freeze_transforms")
            result = mod.freeze_transforms(["pSphere1"], apply=False)
        assert result["success"] is True
        mock_cmds.makeIdentity.assert_not_called()


class TestResetPivot:
    """Tests for reset_pivot script."""

    def test_bbox_center(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "reset_pivot")
            result = mod.reset_pivot(["pSphere1"], mode="bbox_center")
        assert result["success"] is True
        assert result["context"]["updated_objects"][0]["pivot"] == [0.0, 0.0, 0.0]

    def test_world_origin(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "reset_pivot")
            result = mod.reset_pivot(["pSphere1"], mode="world_origin")
        assert result["success"] is True
        assert result["context"]["updated_objects"][0]["pivot"] == [0.0, 0.0, 0.0]

    def test_bottom_mode(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.exactWorldBoundingBox.return_value = [-1.0, 0.0, -1.0, 1.0, 2.0, 1.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "reset_pivot")
            result = mod.reset_pivot(["pSphere1"], mode="bottom")
        assert result["success"] is True
        # y should be bb[1] = 0.0
        assert result["context"]["updated_objects"][0]["pivot"][1] == 0.0

    def test_invalid_mode(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "reset_pivot")
            result = mod.reset_pivot(["pSphere1"], mode="invalid_mode")
        assert result["success"] is False

    def test_no_objects(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "reset_pivot")
            result = mod.reset_pivot([])
        assert result["success"] is False


class TestMatchTransforms:
    """Tests for match_transforms script."""

    def test_match_translate_rotate(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        # xform calls:
        # 1. query target translate
        # 2. xform source set translate (returns None via MagicMock default)
        # 3. query target rotate
        # 4. xform source set rotate (returns None)
        # 5. final query source translate
        # 6. final query source rotate
        # 7. final query source scale
        mock_cmds.xform.side_effect = [
            [1.0, 2.0, 3.0],  # get target translate
            None,  # set source translate
            [10.0, 20.0, 30.0],  # get target rotate
            None,  # set source rotate
            [1.0, 2.0, 3.0],  # final query translate
            [10.0, 20.0, 30.0],  # final query rotate
            [1.0, 1.0, 1.0],  # final query scale
        ]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "match_transforms")
            result = mod.match_transforms("pSphere1", "pCube1")
        assert result["success"] is True
        assert result["context"]["source"] == "pSphere1"

    def test_source_missing(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n == "pCube1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "match_transforms")
            result = mod.match_transforms("missing", "pCube1")
        assert result["success"] is False

    def test_target_missing(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n == "pSphere1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "match_transforms")
            result = mod.match_transforms("pSphere1", "missing")
        assert result["success"] is False


class TestBakeTransforms:
    """Tests for bake_transforms script."""

    def test_bake_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.playbackOptions.side_effect = [1.0, 24.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "bake_transforms")
            result = mod.bake_transforms(["pSphere1"], start_frame=1, end_frame=24)
        assert result["success"] is True
        assert result["context"]["frame_range"] == [1, 24]

    def test_no_objects(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "bake_transforms")
            result = mod.bake_transforms([])
        assert result["success"] is False

    def test_missing_objects(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "bake_transforms")
            result = mod.bake_transforms(["nonexistent"])
        assert result["success"] is False

    def test_uses_playback_defaults(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.playbackOptions.side_effect = [0.0, 120.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-xform-utils", "bake_transforms")
            result = mod.bake_transforms(["pSphere1"])
        assert result["success"] is True
        assert result["context"]["frame_range"] == [0.0, 120.0]


# ---------------------------------------------------------------------------
# maya-spline-ik
# ---------------------------------------------------------------------------


class TestCreateSplineIk:
    """Tests for create_spline_ik script."""

    def test_create_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ikHandle.return_value = ["ikHandle1", "effector1", "curve1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "create_spline_ik")
            result = mod.create_spline_ik("spine_01", "spine_05")
        assert result["success"] is True
        assert result["context"]["ik_handle"] == "ikHandle1"
        assert result["context"]["curve"] == "curve1"

    def test_missing_start_joint(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n == "spine_05"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "create_spline_ik")
            result = mod.create_spline_ik("spine_01", "spine_05")
        assert result["success"] is False

    def test_missing_end_joint(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n == "spine_01"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "create_spline_ik")
            result = mod.create_spline_ik("spine_01", "spine_05")
        assert result["success"] is False

    def test_with_existing_curve(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ikHandle.return_value = ["ikHandle1", "effector1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "create_spline_ik")
            result = mod.create_spline_ik("spine_01", "spine_05", curve="spineCurve")
        assert result["success"] is True
        assert result["context"]["curve"] == "spineCurve"


class TestSetSplineIkTwist:
    """Tests for set_spline_ik_twist script."""

    def test_set_twist(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "set_spline_ik_twist")
            result = mod.set_spline_ik_twist("ikHandle1")
        assert result["success"] is True
        assert result["context"]["ik_handle"] == "ikHandle1"

    def test_missing_handle(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "set_spline_ik_twist")
            result = mod.set_spline_ik_twist("missing_handle")
        assert result["success"] is False

    def test_custom_up_vector(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "set_spline_ik_twist")
            result = mod.set_spline_ik_twist("ikHandle1", up_vector=[0.0, 0.0, 1.0])
        assert result["success"] is True
        assert result["context"]["up_vector"] == [0.0, 0.0, 1.0]


class TestAddStretchToSplineIk:
    """Tests for add_stretch_to_spline_ik script."""

    def test_add_stretch_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = ["curveShape1"]
        mock_cmds.createNode.side_effect = ["ci_node", "md_node"]
        mock_cmds.getAttr.return_value = 10.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "add_stretch_to_spline_ik")
            result = mod.add_stretch_to_spline_ik("ikHandle1", ["spine_01", "spine_02"], "spineCurve")
        assert result["success"] is True
        assert result["context"]["rest_length"] == 10.0

    def test_no_nurbs_shape(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = []  # no shape
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "add_stretch_to_spline_ik")
            result = mod.add_stretch_to_spline_ik("ikHandle1", ["spine_01"], "spineCurve")
        assert result["success"] is False

    def test_invalid_stretch_axis(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = ["curveShape1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "add_stretch_to_spline_ik")
            result = mod.add_stretch_to_spline_ik("ikHandle1", ["spine_01"], "spineCurve", stretch_axis="q")
        assert result["success"] is False


class TestListSplineIkHandles:
    """Tests for list_spline_ik_handles script."""

    def test_list_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["ikHandle1"]
        mock_cmds.ikHandle.side_effect = [
            "ikSplineSolver",  # solver query
            "spine_01",  # startJoint
            "effector1",  # endEffector
        ]
        mock_cmds.listConnections.return_value = ["spineCurve"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "list_spline_ik_handles")
            result = mod.list_spline_ik_handles()
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_no_handles(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "list_spline_ik_handles")
            result = mod.list_spline_ik_handles()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_non_spline_filtered_out(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["ikHandle1", "ikHandle2"]
        # ikHandle1 is ikSCSolver, ikHandle2 is ikSplineSolver
        mock_cmds.ikHandle.side_effect = [
            "ikSCSolver",
            "ikSplineSolver",
            "spine_01",
            "effector1",
        ]
        mock_cmds.listConnections.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-spline-ik", "list_spline_ik_handles")
            result = mod.list_spline_ik_handles()
        assert result["success"] is True
        assert result["context"]["count"] == 1


# ---------------------------------------------------------------------------
# maya-gpu-cache
# ---------------------------------------------------------------------------


class TestExportGpuCache:
    """Tests for export_gpu_cache script."""

    def test_export_success(self, tmp_path):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.playbackOptions.return_value = 1.0
        out_file = str(tmp_path / "out.abc")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": MagicMock()}):
            mod = load_skill_script("maya-gpu-cache", "export_gpu_cache")
            result = mod.export_gpu_cache(["pSphere1"], out_file, start_frame=1.0, end_frame=24.0)
        assert result["success"] is True
        assert result["context"]["file_path"] == out_file

    def test_missing_objects(self, tmp_path):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        mock_cmds.pluginInfo.return_value = True
        out_file = str(tmp_path / "out.abc")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "export_gpu_cache")
            result = mod.export_gpu_cache(["missing"], out_file)
        assert result["success"] is False

    def test_bad_directory(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.pluginInfo.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "export_gpu_cache")
            result = mod.export_gpu_cache(["pSphere1"], "/nonexistent_dir/cache.abc")
        assert result["success"] is False


class TestImportGpuCache:
    """Tests for import_gpu_cache script."""

    def test_import_success(self, tmp_path):
        abc_file = tmp_path / "test.abc"
        abc_file.write_bytes(b"fake_alembic")
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.createNode.side_effect = ["gpuCache_import", "gpuCache_import_cacheShape"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "import_gpu_cache")
            result = mod.import_gpu_cache(str(abc_file))
        assert result["success"] is True
        assert result["context"]["transform_node"] == "gpuCache_import"

    def test_file_not_found(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.pluginInfo.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "import_gpu_cache")
            result = mod.import_gpu_cache("/nonexistent/file.abc")
        assert result["success"] is False


class TestListGpuCaches:
    """Tests for list_gpu_caches script."""

    def test_list_caches(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["gpuCacheShape1"]
        mock_cmds.getAttr.return_value = "/path/to/cache.abc"
        mock_cmds.listRelatives.return_value = ["gpuCache1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "list_gpu_caches")
            result = mod.list_gpu_caches()
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["caches"][0]["file_path"] == "/path/to/cache.abc"

    def test_no_caches(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "list_gpu_caches")
            result = mod.list_gpu_caches()
        assert result["success"] is True
        assert result["context"]["count"] == 0


class TestRefreshGpuCache:
    """Tests for refresh_gpu_cache script."""

    def test_refresh_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "gpuCache"
        mock_cmds.getAttr.return_value = "/path/to/cache.abc"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "refresh_gpu_cache")
            result = mod.refresh_gpu_cache("gpuCacheShape1")
        assert result["success"] is True

    def test_node_not_found(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "refresh_gpu_cache")
            result = mod.refresh_gpu_cache("missing")
        assert result["success"] is False

    def test_wrong_node_type(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-gpu-cache", "refresh_gpu_cache")
            result = mod.refresh_gpu_cache("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-instancer
# ---------------------------------------------------------------------------


class TestCreateInstancer:
    """Tests for create_instancer script."""

    def test_create_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.particleInstancer.return_value = "instancer1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "create_instancer")
            result = mod.create_instancer("nParticle1", ["pSphere1"])
        assert result["success"] is True
        assert result["context"]["instancer_node"] == "instancer1"

    def test_particle_missing(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n != "nParticle1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "create_instancer")
            result = mod.create_instancer("nParticle1", ["pSphere1"])
        assert result["success"] is False

    def test_instance_object_missing(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n == "nParticle1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "create_instancer")
            result = mod.create_instancer("nParticle1", ["missing_geo"])
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-instancer", "create_instancer")
            result = mod.create_instancer("nParticle1", ["pSphere1"])
        assert result["success"] is False


class TestAddInstanceObject:
    """Tests for add_instance_object script."""

    def test_add_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "add_instance_object")
            result = mod.add_instance_object("nParticle1", "instancer1", "pCube1")
        assert result["success"] is True
        assert result["context"]["added_object"] == "pCube1"

    def test_missing_instancer(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.side_effect = lambda n: n != "instancer1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "add_instance_object")
            result = mod.add_instance_object("nParticle1", "instancer1", "pCube1")
        assert result["success"] is False


class TestSetInstancerAttribute:
    """Tests for set_instancer_attribute script."""

    def test_set_object_index(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "set_instancer_attribute")
            result = mod.set_instancer_attribute("nParticle1", "instancer1", "object_index", "objectIndexPP")
        assert result["success"] is True
        assert result["context"]["particle_attribute"] == "objectIndexPP"

    def test_invalid_attribute(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "set_instancer_attribute")
            result = mod.set_instancer_attribute("nParticle1", "instancer1", "invalid_field", "some_attr")
        assert result["success"] is False

    def test_clear_attribute(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "set_instancer_attribute")
            result = mod.set_instancer_attribute("nParticle1", "instancer1", "rotation", None)
        assert result["success"] is True
        assert result["context"]["particle_attribute"] is None


class TestListInstancers:
    """Tests for list_instancers script."""

    def test_list_success(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["instancer1"]
        mock_cmds.listConnections.side_effect = [
            ["nParticle1"],  # inputPoints
            ["pSphere1", "pCube1"],  # inputHierarchy
        ]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "list_instancers")
            result = mod.list_instancers()
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["instancers"][0]["particle_system"] == "nParticle1"

    def test_no_instancers(self):
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-instancer", "list_instancers")
            result = mod.list_instancers()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-instancer", "list_instancers")
            result = mod.list_instancers()
        assert result["success"] is False
