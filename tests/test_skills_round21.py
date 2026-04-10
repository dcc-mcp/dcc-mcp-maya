"""Round 21: tests for maya-constraints-advanced, maya-pipeline, maya-gpu-cache skills."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Dynamically load a skill script module bypassing hyphenated dir names."""
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{0}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "{0}_{1}".format(skill_dir.replace("-", "_"), script_name),
        script_path,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_maya():
    """Return a fresh mock_cmds and wire maya/maya.cmds/maya.utils into sys.modules."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.utils"] = MagicMock()
    sys.modules["maya.api"] = MagicMock()
    return mock_cmds


def _cleanup_maya():
    for mod in ("maya", "maya.cmds", "maya.utils", "maya.api"):
        sys.modules.pop(mod, None)


# ===========================================================================
# maya-constraints-advanced
# ===========================================================================


class TestCreatePathConstraint:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.pathAnimation.return_value = "motionPath1"
        self.mod = _load_script("maya-constraints-advanced", "create_path_constraint")

    def teardown_method(self):
        _cleanup_maya()

    def test_success_basic(self):
        result = self.mod.run({"object": "pSphere1", "curve": "curve1"})
        assert result.success is True
        assert result.context["motion_path"] == "motionPath1"

    def test_missing_object(self):
        result = self.mod.run({"curve": "curve1"})
        assert result.success is False
        assert "required" in result.error.lower()

    def test_missing_curve(self):
        result = self.mod.run({"object": "pSphere1"})
        assert result.success is False

    def test_invalid_axis(self):
        result = self.mod.run({"object": "pSphere1", "curve": "curve1", "front_axis": "w"})
        assert result.success is False
        assert "axis" in result.error.lower()

    def test_follow_false(self):
        result = self.mod.run({"object": "pSphere1", "curve": "curve1", "follow": False})
        assert result.success is True
        kwargs = self.cmds.pathAnimation.call_args[1]
        assert kwargs["follow"] is False

    def test_custom_name(self):
        result = self.mod.run({"object": "pSphere1", "curve": "curve1", "name": "myPath"})
        assert result.success is True
        kwargs = self.cmds.pathAnimation.call_args[1]
        assert kwargs["name"] == "myPath"

    def test_exception(self):
        self.cmds.pathAnimation.side_effect = RuntimeError("bad curve")
        result = self.mod.run({"object": "pSphere1", "curve": "curve1"})
        assert result.success is False
        assert "bad curve" in result.error


class TestCreateRivet:
    def setup_method(self):
        self.cmds = _mock_maya()
        # listRelatives returns shape for first call (shape query), then locator shape
        self.cmds.listRelatives.side_effect = [
            ["pSphereShape1"],  # shape of mesh
            ["rivet_loc_shape"],  # shape of locator
        ]
        self.cmds.nodeType.return_value = "mesh"
        self.cmds.createNode.side_effect = [
            "rivetEdge0_cfe",
            "rivetEdge1_cfe",
            "rivet_loft",
            "rivet_posi",
            "rivet_aimCon",
        ]
        self.cmds.spaceLocator.return_value = ["rivet_loc"]
        self.mod = _load_script("maya-constraints-advanced", "create_rivet")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        result = self.mod.run({"mesh": "pSphere1", "edges": [0, 1]})
        assert result.success is True
        assert result.context["locator"] == "rivet_loc"

    def test_missing_mesh(self):
        result = self.mod.run({"edges": [0, 1]})
        assert result.success is False

    def test_edges_wrong_count(self):
        result = self.mod.run({"mesh": "pSphere1", "edges": [0]})
        assert result.success is False
        assert "2 edge" in result.error

    def test_edges_not_list(self):
        result = self.mod.run({"mesh": "pSphere1", "edges": "bad"})
        assert result.success is False

    def test_custom_name(self):
        self.cmds.listRelatives.side_effect = [
            ["pSphereShape1"],
            ["myRivet_shape"],
        ]
        self.cmds.createNode.side_effect = [
            "rivetEdge0_cfe",
            "rivetEdge1_cfe",
            "rivet_loft",
            "rivet_posi",
            "rivet_aimCon",
        ]
        self.cmds.spaceLocator.return_value = ["myRivet"]
        result = self.mod.run({"mesh": "pSphere1", "edges": [2, 3], "name": "myRivet"})
        assert result.success is True
        call_args = self.cmds.spaceLocator.call_args
        assert call_args[1]["name"] == "myRivet"

    def test_exception(self):
        self.cmds.createNode.side_effect = RuntimeError("node error")
        result = self.mod.run({"mesh": "pSphere1", "edges": [0, 1]})
        assert result.success is False
        assert "node error" in result.error


class TestCreateTangentConstraint:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.tangentConstraint.return_value = ["tangentConstraint1"]
        self.mod = _load_script("maya-constraints-advanced", "create_tangent_constraint")

    def teardown_method(self):
        _cleanup_maya()

    def test_success_basic(self):
        result = self.mod.run({"target": "curve1", "object": "pSphere1"})
        assert result.success is True
        assert result.context["constraint"] == "tangentConstraint1"

    def test_missing_target(self):
        result = self.mod.run({"object": "pSphere1"})
        assert result.success is False

    def test_missing_object(self):
        result = self.mod.run({"target": "curve1"})
        assert result.success is False

    def test_custom_aim_up_vectors(self):
        result = self.mod.run({
            "target": "curve1",
            "object": "pSphere1",
            "aim_vector": [0, 1, 0],
            "up_vector": [1, 0, 0],
            "weight": 0.5,
        })
        assert result.success is True
        kwargs = self.cmds.tangentConstraint.call_args[1]
        assert kwargs["aimVector"] == [0, 1, 0]
        assert kwargs["weight"] == 0.5

    def test_custom_name(self):
        result = self.mod.run({
            "target": "curve1", "object": "pSphere1", "name": "myTangent"
        })
        assert result.success is True
        kwargs = self.cmds.tangentConstraint.call_args[1]
        assert kwargs["name"] == "myTangent"

    def test_exception(self):
        self.cmds.tangentConstraint.side_effect = RuntimeError("no curve")
        result = self.mod.run({"target": "curve1", "object": "pSphere1"})
        assert result.success is False


class TestCreateClosestPointConstraint:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.listRelatives.return_value = ["pSphereShape1"]
        self.cmds.nodeType.return_value = "mesh"
        self.cmds.objExists.return_value = True
        self.cmds.createNode.side_effect = ["closestPOM"]
        self.cmds.spaceLocator.return_value = ["pSphere1_cpLoc"]
        self.cmds.pointConstraint.return_value = ["pointConstraint1"]
        self.mod = _load_script("maya-constraints-advanced", "create_closest_point_constraint")

    def teardown_method(self):
        _cleanup_maya()

    def test_success_mesh(self):
        result = self.mod.run({"object": "pCube1", "target": "pSphere1"})
        assert result.success is True
        assert "closestPOM" in result.context["closest_point_node"]

    def test_missing_object(self):
        result = self.mod.run({"target": "pSphere1"})
        assert result.success is False

    def test_missing_target(self):
        result = self.mod.run({"object": "pCube1"})
        assert result.success is False

    def test_nurbs_surface_path(self):
        self.cmds.nodeType.return_value = "nurbsSurface"
        self.cmds.createNode.side_effect = ["closestPOS"]
        result = self.mod.run({"object": "pCube1", "target": "nurbsPlane1"})
        assert result.success is True

    def test_with_normal_constraint(self):
        self.cmds.normalConstraint = MagicMock(return_value=["normalConstraint1"])
        result = self.mod.run({
            "object": "pCube1",
            "target": "pSphere1",
            "point_constraint_only": False,
        })
        assert result.success is True

    def test_exception(self):
        self.cmds.createNode.side_effect = RuntimeError("bad")
        result = self.mod.run({"object": "pCube1", "target": "pSphere1"})
        assert result.success is False


class TestListMotionPaths:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.ls.return_value = ["motionPath1", "motionPath2"]
        self.cmds.listConnections.side_effect = [
            ["pSphere1"],   # motionPath1 driven
            ["curve1"],     # motionPath1 curve
            ["pCube1"],     # motionPath2 driven
            ["curve2"],     # motionPath2 curve
        ]
        self.cmds.getAttr.return_value = 0.5
        self.mod = _load_script("maya-constraints-advanced", "list_motion_paths")

    def teardown_method(self):
        _cleanup_maya()

    def test_list_all(self):
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_filter_by_object(self):
        self.cmds.listConnections.side_effect = [
            ["pSphere1"],
            ["curve1"],
            ["pCube1"],
            ["curve2"],
        ]
        result = self.mod.run({"object_filter": "pCube1"})
        assert result.success is True
        assert result.context["count"] == 1

    def test_no_motion_paths(self):
        self.cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_getattr_exception_handled(self):
        self.cmds.getAttr.side_effect = RuntimeError("attr error")
        result = self.mod.run({})
        assert result.success is True  # graceful degradation

    def test_exception(self):
        self.cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


# ===========================================================================
# maya-pipeline
# ===========================================================================


class TestGetSceneMetadata:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.fileInfo.return_value = ["project", "my_project", "artist", "alice"]
        self.mod = _load_script("maya-pipeline", "get_scene_metadata")

    def teardown_method(self):
        _cleanup_maya()

    def test_get_all(self):
        result = self.mod.run({})
        assert result.success is True
        assert result.context["metadata"]["project"] == "my_project"
        assert result.context["metadata"]["artist"] == "alice"

    def test_filter_by_keys(self):
        result = self.mod.run({"keys": ["project"]})
        assert result.success is True
        assert "project" in result.context["metadata"]
        assert "artist" not in result.context["metadata"]

    def test_key_not_found(self):
        result = self.mod.run({"keys": ["nonexistent_key"]})
        assert result.success is True
        assert result.context["count"] == 0

    def test_empty_fileinfo(self):
        self.cmds.fileInfo.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_exception(self):
        self.cmds.fileInfo.side_effect = RuntimeError("query failed")
        result = self.mod.run({})
        assert result.success is False


class TestSetSceneMetadata:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.mod = _load_script("maya-pipeline", "set_scene_metadata")

    def teardown_method(self):
        _cleanup_maya()

    def test_write_metadata(self):
        result = self.mod.run({"metadata": {"project": "my_project", "artist": "bob"}})
        assert result.success is True
        assert "project" in result.context["written_keys"]
        assert "artist" in result.context["written_keys"]

    def test_empty_metadata(self):
        result = self.mod.run({"metadata": {}})
        assert result.success is False

    def test_missing_metadata(self):
        result = self.mod.run({})
        assert result.success is False

    def test_values_coerced_to_str(self):
        result = self.mod.run({"metadata": {"frame": 42, "enabled": True}})
        assert result.success is True

    def test_exception(self):
        self.cmds.fileInfo.side_effect = RuntimeError("write failed")
        result = self.mod.run({"metadata": {"key": "val"}})
        assert result.success is False


class TestTagAsset:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.attributeQuery.return_value = False  # attrs don't exist yet
        self.mod = _load_script("maya-pipeline", "tag_asset")

    def teardown_method(self):
        _cleanup_maya()

    def test_tag_success(self):
        result = self.mod.run({
            "node": "hero_geo",
            "asset_name": "hero_char",
            "asset_type": "character",
            "step": "rigging",
        })
        assert result.success is True
        assert len(result.context["written_attributes"]) >= 3

    def test_missing_node(self):
        result = self.mod.run({"asset_name": "hero"})
        assert result.success is False

    def test_node_not_exists(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"node": "nonexistent"})
        assert result.success is False
        assert "not exist" in result.error

    def test_existing_attr_updated(self):
        self.cmds.attributeQuery.return_value = True  # attrs already exist
        result = self.mod.run({"node": "hero_geo", "version": "v002"})
        assert result.success is True
        # addAttr should NOT have been called
        self.cmds.addAttr.assert_not_called()

    def test_no_empty_values_written(self):
        result = self.mod.run({"node": "hero_geo", "asset_name": "hero"})
        assert result.success is True
        # Only asset_name should have been written
        assert "pipeline_asset_name" in result.context["written_attributes"]
        assert "pipeline_shot" not in result.context["written_attributes"]

    def test_exception(self):
        self.cmds.addAttr.side_effect = RuntimeError("add failed")
        result = self.mod.run({"node": "hero_geo", "asset_name": "hero"})
        assert result.success is False


class TestGetAssetTags:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.attributeQuery.return_value = True
        self.cmds.getAttr.return_value = "hero_char"
        self.mod = _load_script("maya-pipeline", "get_asset_tags")

    def teardown_method(self):
        _cleanup_maya()

    def test_get_tags(self):
        result = self.mod.run({"node": "hero_geo"})
        assert result.success is True
        assert "pipeline_asset_name" in result.context["tags"]

    def test_missing_node(self):
        result = self.mod.run({})
        assert result.success is False

    def test_node_not_exists(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"node": "gone"})
        assert result.success is False

    def test_no_attrs(self):
        self.cmds.attributeQuery.return_value = False
        result = self.mod.run({"node": "untagged_geo"})
        assert result.success is True
        assert len(result.context["tags"]) == 0

    def test_exception(self):
        self.cmds.getAttr.side_effect = RuntimeError("getAttr failed")
        result = self.mod.run({"node": "hero_geo"})
        assert result.success is False


class TestListTaggedAssets:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.ls.return_value = ["hero_geo", "prop_rock"]
        self.cmds.attributeQuery.return_value = True

        def _getattr_side(attr_str):
            if "asset_type" in attr_str:
                return "character" if "hero" in attr_str else "prop"
            if "step" in attr_str:
                return "rigging"
            return "some_val"

        self.cmds.getAttr.side_effect = _getattr_side
        self.mod = _load_script("maya-pipeline", "list_tagged_assets")

    def teardown_method(self):
        _cleanup_maya()

    def test_list_all(self):
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_filter_by_asset_type(self):
        result = self.mod.run({"asset_type_filter": "character"})
        assert result.success is True
        assert result.context["count"] == 1

    def test_no_tagged_nodes(self):
        self.cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_filter_by_step(self):
        result = self.mod.run({"step_filter": "rigging"})
        assert result.success is True

    def test_exception(self):
        self.cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


# ===========================================================================
# maya-gpu-cache
# ===========================================================================


class TestExportGpuCache:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.currentTime.return_value = 1
        self.cmds.pluginInfo.return_value = True
        self.mod = _load_script("maya-gpu-cache", "export_gpu_cache")

    def teardown_method(self):
        _cleanup_maya()

    def test_success_with_objects(self):
        with patch("os.makedirs"), patch("os.path.join", return_value="/tmp/gpu_cache.abc"):
            result = self.mod.run({
                "objects": ["pSphere1"],
                "output_dir": "/tmp",
                "filename": "gpu_cache",
            })
        assert result.success is True

    def test_missing_output_dir(self):
        result = self.mod.run({"objects": ["pSphere1"]})
        assert result.success is False
        assert "output_dir" in result.error

    def test_missing_objects_and_no_all_dag(self):
        result = self.mod.run({"output_dir": "/tmp"})
        assert result.success is False

    def test_all_dag_objects(self):
        with patch("os.makedirs"), patch("os.path.join", return_value="/tmp/scene.abc"):
            result = self.mod.run({
                "output_dir": "/tmp",
                "all_dagobjects": True,
                "filename": "scene",
            })
        assert result.success is True
        kwargs = self.cmds.gpuCache.call_args[1]
        assert kwargs.get("allDagObjects") is True

    def test_plugin_not_loaded(self):
        self.cmds.pluginInfo.return_value = False
        with patch("os.makedirs"), patch("os.path.join", return_value="/tmp/x.abc"):
            result = self.mod.run({
                "objects": ["pSphere1"],
                "output_dir": "/tmp",
            })
        assert result.success is True
        self.cmds.loadPlugin.assert_called_once_with("gpuCache")

    def test_exception(self):
        self.cmds.gpuCache.side_effect = RuntimeError("export failed")
        with patch("os.makedirs"):
            result = self.mod.run({
                "objects": ["pSphere1"],
                "output_dir": "/tmp",
            })
        assert result.success is False


class TestImportGpuCache:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.pluginInfo.return_value = True
        self.cmds.createNode.side_effect = ["gpuCacheTransform", "gpuCacheTransform_gpuCacheShape"]
        self.mod = _load_script("maya-gpu-cache", "import_gpu_cache")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        with patch("os.path.exists", return_value=True):
            result = self.mod.run({"file_path": "/path/to/cache.abc"})
        assert result.success is True
        assert result.context["file_path"] == "/path/to/cache.abc"

    def test_missing_file_path(self):
        result = self.mod.run({})
        assert result.success is False

    def test_file_not_found(self):
        with patch("os.path.exists", return_value=False):
            result = self.mod.run({"file_path": "/nonexistent.abc"})
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_custom_node_name(self):
        with patch("os.path.exists", return_value=True):
            self.cmds.createNode.side_effect = ["myAsset", "myAsset_gpuCacheShape"]
            result = self.mod.run({"file_path": "/path/to/cache.abc", "node_name": "myAsset"})
        assert result.success is True

    def test_plugin_not_loaded(self):
        self.cmds.pluginInfo.return_value = False
        with patch("os.path.exists", return_value=True):
            result = self.mod.run({"file_path": "/path/to/cache.abc"})
        assert result.success is True
        self.cmds.loadPlugin.assert_called_once_with("gpuCache")

    def test_exception(self):
        self.cmds.createNode.side_effect = RuntimeError("node error")
        with patch("os.path.exists", return_value=True):
            result = self.mod.run({"file_path": "/path/to/cache.abc"})
        assert result.success is False


class TestListGpuCaches:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.ls.return_value = ["gpuCacheShape1", "gpuCacheShape2"]
        self.cmds.getAttr.return_value = "/path/to/cache.abc"
        self.cmds.listRelatives.return_value = ["gpuCacheTransform1"]
        self.mod = _load_script("maya-gpu-cache", "list_gpu_caches")

    def teardown_method(self):
        _cleanup_maya()

    def test_list_all(self):
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_no_gpu_caches(self):
        self.cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_file_path_in_result(self):
        result = self.mod.run({})
        assert result.success is True
        caches = result.context["gpu_caches"]
        assert caches[0]["file_path"] == "/path/to/cache.abc"

    def test_exception(self):
        self.cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


class TestDeleteGpuCache:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.nodeType.return_value = "gpuCache"
        self.cmds.listRelatives.return_value = ["gpuCacheTransform1"]
        self.mod = _load_script("maya-gpu-cache", "delete_gpu_cache")

    def teardown_method(self):
        _cleanup_maya()

    def test_delete_shape(self):
        result = self.mod.run({"node": "gpuCacheShape1"})
        assert result.success is True
        assert "gpuCacheShape1" in result.context["deleted_nodes"]

    def test_delete_via_transform(self):
        self.cmds.nodeType.side_effect = ["transform", "gpuCache"]
        self.cmds.listRelatives.side_effect = [
            ["gpuCacheShape1"],    # shapes of transform
            ["gpuCacheTransform1"],  # parent of shape
        ]
        result = self.mod.run({"node": "gpuCacheTransform1"})
        assert result.success is True

    def test_missing_node(self):
        result = self.mod.run({})
        assert result.success is False

    def test_node_not_exists(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"node": "gone"})
        assert result.success is False

    def test_not_gpu_cache(self):
        self.cmds.nodeType.return_value = "mesh"
        self.cmds.listRelatives.return_value = []
        result = self.mod.run({"node": "pSphere1"})
        assert result.success is False
        assert "not a gpucache" in result.error.lower()

    def test_exception(self):
        self.cmds.delete.side_effect = RuntimeError("delete failed")
        result = self.mod.run({"node": "gpuCacheShape1"})
        assert result.success is False


class TestSetGpuCacheAttribute:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.attributeQuery.return_value = True
        self.mod = _load_script("maya-gpu-cache", "set_gpu_cache_attribute")

    def teardown_method(self):
        _cleanup_maya()

    def test_set_string_attr(self):
        result = self.mod.run({
            "node": "gpuCacheShape1",
            "attribute": "cacheFileName",
            "value": "/new/path.abc",
        })
        assert result.success is True
        self.cmds.setAttr.assert_called_once()

    def test_set_numeric_attr(self):
        result = self.mod.run({
            "node": "gpuCacheShape1",
            "attribute": "visibility",
            "value": 0,
        })
        assert result.success is True

    def test_missing_node(self):
        result = self.mod.run({"attribute": "visibility", "value": 1})
        assert result.success is False

    def test_missing_attribute(self):
        result = self.mod.run({"node": "gpuCacheShape1", "value": 1})
        assert result.success is False

    def test_node_not_exists(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"node": "gone", "attribute": "visibility", "value": 1})
        assert result.success is False

    def test_attribute_not_found(self):
        self.cmds.attributeQuery.return_value = False
        result = self.mod.run({
            "node": "gpuCacheShape1",
            "attribute": "nonexistent",
            "value": 1,
        })
        assert result.success is False
        assert "does not exist" in result.error.lower()

    def test_list_value(self):
        result = self.mod.run({
            "node": "gpuCacheShape1",
            "attribute": "someVec",
            "value": [1.0, 2.0, 3.0],
        })
        assert result.success is True

    def test_exception(self):
        self.cmds.setAttr.side_effect = RuntimeError("set failed")
        result = self.mod.run({
            "node": "gpuCacheShape1",
            "attribute": "visibility",
            "value": 1,
        })
        assert result.success is False
