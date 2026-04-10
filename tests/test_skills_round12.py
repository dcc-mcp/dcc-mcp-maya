"""Round 12 skill tests: remaining uncovered scripts across multiple skill groups.

Covers:
- maya-scene-utils: create_annotation, create_polygon_text, toggle_gpu_override
- maya-uv-ops: copy_uvs, delete_uv_set, get_uv_shell_info
- maya-vertex-color: remove_vertex_colors
- maya-deformers: sculpt_deformer, set_cluster_weights

All Maya API calls are mocked; no real Maya installation required.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def _load_script(skill_dir, script_name):
    """Load a skill script via importlib to handle hyphenated directory names."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r12_{}_{}_{}".format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, modules_dict) with sensible defaults."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }
    return maya_mock, cmds_mock, modules


def _run_func(skill_dir, func_name, cmds_overrides=None, **kwargs):
    """Load a skill script, inject Maya mocks, and call its ``main`` function."""
    cmds_overrides = cmds_overrides or {}
    _, cmds_mock, modules = _make_maya_env(**cmds_overrides)
    with patch.dict(sys.modules, modules):
        mod = _load_script(skill_dir, func_name)
        result = mod.main(**kwargs)
    return result


# ===========================================================================
# maya-scene-utils: create_annotation
# ===========================================================================


class TestCreateAnnotation:
    def test_basic_success(self):
        cmds_ov = {
            "annotate": MagicMock(return_value="annotationShape1"),
            "listRelatives": MagicMock(return_value=["annotation1"]),
            "xform": MagicMock(return_value=[0.0, 0.0, 0.0]),
        }
        result = _run_func("maya-scene-utils", "create_annotation", cmds_ov,
                           object_name="pSphere1", text="test label")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"
        assert result["context"]["text"] == "test label"

    def test_with_explicit_position(self):
        cmds_ov = {
            "annotate": MagicMock(return_value="annotationShape1"),
            "listRelatives": MagicMock(return_value=["annotation1"]),
        }
        result = _run_func("maya-scene-utils", "create_annotation", cmds_ov,
                           object_name="pCube1", text="label", position=[1.0, 2.0, 3.0])
        assert result["success"] is True
        assert result["context"]["position"] == [1.0, 2.0, 3.0]

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene-utils", "create_annotation", cmds_ov,
                           object_name="missing", text="x")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_empty_text(self):
        result = _run_func("maya-scene-utils", "create_annotation", {},
                           object_name="pSphere1", text="")
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_invalid_position_length(self):
        result = _run_func("maya-scene-utils", "create_annotation", {},
                           object_name="pSphere1", text="label", position=[1.0, 2.0])
        assert result["success"] is False
        assert "invalid position" in result["message"].lower()

    def test_annotation_shape_no_parent(self):
        # listRelatives returns None — ann_parent is falsy, use shape name directly
        cmds_ov = {
            "annotate": MagicMock(return_value="annotationShape1"),
            "listRelatives": MagicMock(return_value=None),
            "xform": MagicMock(return_value=[0.0, 0.0, 0.0]),
        }
        result = _run_func("maya-scene-utils", "create_annotation", cmds_ov,
                           object_name="pSphere1", text="hello")
        assert result["success"] is True
        assert result["context"]["annotation_transform"] == "annotationShape1"

    def test_exception_handling(self):
        cmds_ov = {"annotate": MagicMock(side_effect=RuntimeError("oops"))}
        result = _run_func("maya-scene-utils", "create_annotation", cmds_ov,
                           object_name="pSphere1", text="label")
        assert result["success"] is False


# ===========================================================================
# maya-scene-utils: create_polygon_text
# ===========================================================================


class TestCreatePolygonText:
    def test_basic_success_with_extrude(self):
        cmds_ov = {
            "textCurves": MagicMock(return_value=["curve1", "curve2"]),
            "extrude": MagicMock(return_value=["mesh1", "mesh2"]),
        }
        result = _run_func("maya-scene-utils", "create_polygon_text", cmds_ov,
                           text="Hello", extrude=True)
        assert result["success"] is True
        assert result["context"]["text"] == "Hello"
        assert result["context"]["extruded"] is True

    def test_curves_only_no_extrude(self):
        cmds_ov = {
            "textCurves": MagicMock(return_value=["curve1"]),
        }
        result = _run_func("maya-scene-utils", "create_polygon_text", cmds_ov,
                           text="Hi", extrude=False)
        assert result["success"] is True
        assert result["context"]["extruded"] is False
        assert result["context"]["objects"] == ["curve1"]

    def test_empty_text(self):
        result = _run_func("maya-scene-utils", "create_polygon_text", {},
                           text="")
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_with_custom_name_and_font(self):
        cmds_ov = {
            "textCurves": MagicMock(return_value=["c1"]),
            "extrude": MagicMock(return_value=["m1"]),
        }
        result = _run_func("maya-scene-utils", "create_polygon_text", cmds_ov,
                           text="A", name="myText", font="Courier", depth=1.0)
        assert result["success"] is True
        assert result["context"]["font"] == "Courier"

    def test_extrude_exception_falls_back_to_curve(self):
        # When extrude raises, the curve itself is appended to extruded list
        cmds_ov = {
            "textCurves": MagicMock(return_value=["curve1"]),
            "extrude": MagicMock(side_effect=Exception("gpu error")),
        }
        result = _run_func("maya-scene-utils", "create_polygon_text", cmds_ov,
                           text="X", extrude=True)
        assert result["success"] is True
        assert "curve1" in result["context"]["objects"]

    def test_exception_handling(self):
        cmds_ov = {"textCurves": MagicMock(side_effect=RuntimeError("crash"))}
        result = _run_func("maya-scene-utils", "create_polygon_text", cmds_ov,
                           text="err")
        assert result["success"] is False


# ===========================================================================
# maya-scene-utils: toggle_gpu_override
# ===========================================================================


class TestToggleGpuOverride:
    def test_enable(self):
        result = _run_func("maya-scene-utils", "toggle_gpu_override", {},
                           object_name="pSphere1", enabled=True)
        assert result["success"] is True
        assert result["context"]["enabled"] is True
        assert result["context"]["display_type"] == 2

    def test_disable(self):
        result = _run_func("maya-scene-utils", "toggle_gpu_override", {},
                           object_name="pSphere1", enabled=False)
        assert result["success"] is True
        assert result["context"]["enabled"] is False
        assert result["context"]["display_type"] == 0

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene-utils", "toggle_gpu_override", cmds_ov,
                           object_name="missing", enabled=True)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_exception_handling(self):
        cmds_ov = {"setAttr": MagicMock(side_effect=RuntimeError("attr error"))}
        result = _run_func("maya-scene-utils", "toggle_gpu_override", cmds_ov,
                           object_name="pSphere1", enabled=True)
        assert result["success"] is False

    def test_default_enabled_is_true(self):
        result = _run_func("maya-scene-utils", "toggle_gpu_override", {},
                           object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["enabled"] is True


# ===========================================================================
# maya-uv-ops: copy_uvs
# ===========================================================================


class TestCopyUvs:
    def test_basic_success(self):
        result = _run_func("maya-uv-ops", "copy_uvs", {},
                           source="pSphere1", target="pCube1")
        assert result["success"] is True
        assert result["context"]["source"] == "pSphere1"
        assert result["context"]["target"] == "pCube1"

    def test_source_not_found(self):
        cmds_ov = {"objExists": MagicMock(side_effect=lambda n: n != "pSphere1")}
        result = _run_func("maya-uv-ops", "copy_uvs", cmds_ov,
                           source="pSphere1", target="pCube1")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_target_not_found(self):
        cmds_ov = {"objExists": MagicMock(side_effect=lambda n: n != "pCube1")}
        result = _run_func("maya-uv-ops", "copy_uvs", cmds_ov,
                           source="pSphere1", target="pCube1")
        assert result["success"] is False

    def test_with_uv_set_names(self):
        result = _run_func("maya-uv-ops", "copy_uvs", {},
                           source="pSphere1", target="pCube1",
                           source_uv_set="map1", target_uv_set="map2")
        assert result["success"] is True
        assert result["context"]["source_uv_set"] == "map1"
        assert result["context"]["target_uv_set"] == "map2"

    def test_exception_handling(self):
        cmds_ov = {"transferAttributes": MagicMock(side_effect=RuntimeError("fail"))}
        result = _run_func("maya-uv-ops", "copy_uvs", cmds_ov,
                           source="pSphere1", target="pCube1")
        assert result["success"] is False


# ===========================================================================
# maya-uv-ops: delete_uv_set
# ===========================================================================


class TestDeleteUvSet:
    def test_basic_success(self):
        cmds_ov = {
            "polyUVSet": MagicMock(return_value=["map1", "map2"]),
        }
        result = _run_func("maya-uv-ops", "delete_uv_set", cmds_ov,
                           object_name="pSphere1", uv_set_name="map2")
        assert result["success"] is True
        assert result["context"]["uv_set_name"] == "map2"

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-uv-ops", "delete_uv_set", cmds_ov,
                           object_name="missing", uv_set_name="map1")
        assert result["success"] is False

    def test_uv_set_not_found(self):
        cmds_ov = {
            "polyUVSet": MagicMock(return_value=["map1"]),
        }
        result = _run_func("maya-uv-ops", "delete_uv_set", cmds_ov,
                           object_name="pSphere1", uv_set_name="nonexistent")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_cannot_delete_only_uv_set(self):
        cmds_ov = {
            "polyUVSet": MagicMock(return_value=["map1"]),
        }
        result = _run_func("maya-uv-ops", "delete_uv_set", cmds_ov,
                           object_name="pSphere1", uv_set_name="map1")
        assert result["success"] is False
        assert "only" in result["message"].lower()

    def test_exception_handling(self):
        cmds_ov = {
            "polyUVSet": MagicMock(side_effect=RuntimeError("crash")),
        }
        result = _run_func("maya-uv-ops", "delete_uv_set", cmds_ov,
                           object_name="pSphere1", uv_set_name="map2")
        assert result["success"] is False


# ===========================================================================
# maya-uv-ops: get_uv_shell_info
# ===========================================================================


class TestGetUvShellInfo:
    def _make_poly_uv_set_mock(self, all_sets=None, current_set="map1"):
        """Build a side_effect function for cmds.polyUVSet queries."""
        all_sets = all_sets or ["map1"]

        def _poly_uv_set(obj, **kwargs):
            if kwargs.get("query") and kwargs.get("allUVSets"):
                return list(all_sets)
            if kwargs.get("query") and kwargs.get("currentUVSet"):
                return current_set
            return None

        return _poly_uv_set

    def test_basic_success(self):
        poly_uv_set = self._make_poly_uv_set_mock()
        cmds_ov = {
            "polyUVSet": MagicMock(side_effect=poly_uv_set),
            "polyEvaluate": MagicMock(return_value=[0, 1, 0, 1]),  # shell_ids
            "polyEditUV": MagicMock(return_value=[0.0, 0.5, 1.0, 0.5]),
        }
        result = _run_func("maya-uv-ops", "get_uv_shell_info", cmds_ov,
                           object_name="pSphere1")
        assert result["success"] is True
        assert "shell_count" in result["context"]

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-uv-ops", "get_uv_shell_info", cmds_ov,
                           object_name="missing")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_with_named_uv_set(self):
        def _poly_uv_set(obj, **kwargs):
            if kwargs.get("query") and kwargs.get("allUVSets"):
                return ["map1", "map2"]
            if kwargs.get("query") and kwargs.get("currentUVSet"):
                return "map2"
            return None

        cmds_ov = {
            "polyUVSet": MagicMock(side_effect=_poly_uv_set),
            "polyEvaluate": MagicMock(return_value=[]),
            "polyEditUV": MagicMock(return_value=[]),
        }
        result = _run_func("maya-uv-ops", "get_uv_shell_info", cmds_ov,
                           object_name="pSphere1", uv_set="map2")
        assert result["success"] is True

    def test_uv_set_not_found(self):
        def _poly_uv_set(obj, **kwargs):
            if kwargs.get("query") and kwargs.get("allUVSets"):
                return ["map1"]
            return None

        cmds_ov = {
            "polyUVSet": MagicMock(side_effect=_poly_uv_set),
        }
        result = _run_func("maya-uv-ops", "get_uv_shell_info", cmds_ov,
                           object_name="pSphere1", uv_set="missing_set")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_exception_handling(self):
        cmds_ov = {
            "polyUVSet": MagicMock(side_effect=RuntimeError("uv error")),
        }
        result = _run_func("maya-uv-ops", "get_uv_shell_info", cmds_ov,
                           object_name="pSphere1")
        assert result["success"] is False


# ===========================================================================
# maya-vertex-color: remove_vertex_colors
# ===========================================================================


class TestRemoveVertexColors:
    def test_remove_specific_color_set(self):
        cmds_ov = {
            "polyColorSet": MagicMock(return_value=["colorSet1", "colorSet2"]),
        }
        result = _run_func("maya-vertex-color", "remove_vertex_colors", cmds_ov,
                           object_name="pSphere1", color_set="colorSet1")
        assert result["success"] is True
        assert "colorSet1" in result["context"]["removed_color_sets"]

    def test_remove_all_color_sets(self):
        cmds_ov = {
            "polyColorSet": MagicMock(return_value=["colorSet1", "colorSet2"]),
        }
        result = _run_func("maya-vertex-color", "remove_vertex_colors", cmds_ov,
                           object_name="pSphere1")
        assert result["success"] is True
        assert len(result["context"]["removed_color_sets"]) == 2

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-vertex-color", "remove_vertex_colors", cmds_ov,
                           object_name="missing")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_color_set_not_found(self):
        cmds_ov = {
            "polyColorSet": MagicMock(return_value=["colorSet1"]),
        }
        result = _run_func("maya-vertex-color", "remove_vertex_colors", cmds_ov,
                           object_name="pSphere1", color_set="nonexistent")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_exception_handling(self):
        cmds_ov = {
            "polyColorSet": MagicMock(side_effect=RuntimeError("boom")),
        }
        result = _run_func("maya-vertex-color", "remove_vertex_colors", cmds_ov,
                           object_name="pSphere1", color_set="colorSet1")
        assert result["success"] is False


# ===========================================================================
# maya-deformers: sculpt_deformer
# ===========================================================================


class TestSculptDeformer:
    def test_basic_success_stretch(self):
        cmds_ov = {
            "sculpt": MagicMock(return_value=["sculptNode1", "sculptSphere1", "sculptOrigin1"]),
        }
        result = _run_func("maya-deformers", "sculpt_deformer", cmds_ov,
                           objects=["pSphere1"], mode="stretch")
        assert result["success"] is True
        assert result["context"]["sculpt_node"] == "sculptNode1"
        assert result["context"]["mode"] == "stretch"

    def test_project_mode(self):
        cmds_ov = {
            "sculpt": MagicMock(return_value=["sculptNode1", "sculptSphere1", "sculptOrigin1"]),
        }
        result = _run_func("maya-deformers", "sculpt_deformer", cmds_ov,
                           objects=["pCube1"], mode="project")
        assert result["success"] is True
        assert result["context"]["mode"] == "project"

    def test_flip_mode(self):
        cmds_ov = {
            "sculpt": MagicMock(return_value=["sN", "sS", "sO"]),
        }
        result = _run_func("maya-deformers", "sculpt_deformer", cmds_ov,
                           objects=["pCube1"], mode="flip")
        assert result["success"] is True

    def test_invalid_mode(self):
        result = _run_func("maya-deformers", "sculpt_deformer", {},
                           objects=["pSphere1"], mode="invalid")
        assert result["success"] is False
        assert "invalid mode" in result["message"].lower()

    def test_empty_objects(self):
        result = _run_func("maya-deformers", "sculpt_deformer", {},
                           objects=[], mode="stretch")
        assert result["success"] is False
        assert "no objects" in result["message"].lower()

    def test_missing_object(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-deformers", "sculpt_deformer", cmds_ov,
                           objects=["missing"], mode="stretch")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_exception_handling(self):
        cmds_ov = {"sculpt": MagicMock(side_effect=RuntimeError("sculpt error"))}
        result = _run_func("maya-deformers", "sculpt_deformer", cmds_ov,
                           objects=["pSphere1"], mode="stretch")
        assert result["success"] is False


# ===========================================================================
# maya-deformers: set_cluster_weights
# ===========================================================================


class TestSetClusterWeights:
    def test_basic_success_all_vertices(self):
        cmds_ov = {
            "polyEvaluate": MagicMock(return_value=3),
        }
        result = _run_func("maya-deformers", "set_cluster_weights", cmds_ov,
                           cluster_node="cluster1", mesh="pSphere1",
                           weights=[0.5, 0.8, 1.0])
        assert result["success"] is True
        assert result["context"]["vertex_count"] == 3

    def test_specific_vertex_indices(self):
        cmds_ov = {
            "polyEvaluate": MagicMock(return_value=100),
        }
        result = _run_func("maya-deformers", "set_cluster_weights", cmds_ov,
                           cluster_node="cluster1", mesh="pSphere1",
                           weights=[0.5, 1.0], vertex_indices=[0, 5])
        assert result["success"] is True
        assert result["context"]["vertex_count"] == 2

    def test_no_weights(self):
        result = _run_func("maya-deformers", "set_cluster_weights", {},
                           cluster_node="cluster1", mesh="pSphere1",
                           weights=[])
        assert result["success"] is False
        assert "no weights" in result["message"].lower()

    def test_cluster_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-deformers", "set_cluster_weights", cmds_ov,
                           cluster_node="missing", mesh="pSphere1",
                           weights=[0.5])
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_mesh_not_found(self):
        def obj_exists(name):
            return name == "cluster1"

        cmds_ov = {"objExists": MagicMock(side_effect=obj_exists)}
        result = _run_func("maya-deformers", "set_cluster_weights", cmds_ov,
                           cluster_node="cluster1", mesh="missing",
                           weights=[0.5])
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_weight_count_mismatch(self):
        cmds_ov = {
            "polyEvaluate": MagicMock(return_value=5),
        }
        result = _run_func("maya-deformers", "set_cluster_weights", cmds_ov,
                           cluster_node="cluster1", mesh="pSphere1",
                           weights=[0.5, 1.0])  # only 2 weights for 5-vertex mesh
        assert result["success"] is False
        assert "mismatch" in result["message"].lower()

    def test_normalize_clamps_weights(self):
        cmds_ov = {
            "polyEvaluate": MagicMock(return_value=2),
        }
        result = _run_func("maya-deformers", "set_cluster_weights", cmds_ov,
                           cluster_node="cluster1", mesh="pSphere1",
                           weights=[-0.5, 1.5], normalize=True)
        assert result["success"] is True

    def test_exception_handling(self):
        cmds_ov = {
            "polyEvaluate": MagicMock(side_effect=RuntimeError("eval error")),
        }
        result = _run_func("maya-deformers", "set_cluster_weights", cmds_ov,
                           cluster_node="cluster1", mesh="pSphere1",
                           weights=[0.5])
        assert result["success"] is False
