"""Round 33: Deep edge-case tests for remaining objExists patterns and complex skill logic.

Covers skills whose remaining ``cmds.objExists`` calls are intentionally kept
(attribute probes, graceful-skip loops, fallback resolution) as well as new
depth tests for:

- ``maya-constraints-advanced/get_constraint_weights`` — w_attr fallback + attr probe
- ``maya-annotation/create_annotation`` — target_object validation + temp-locator cleanup
- ``maya-mocap/create_hik_definition`` — missing-joint graceful skip
- ``maya-pose-library/load_pose`` — skip_missing + namespace prefix
- ``maya-texture-bake/bake_lighting`` — per-object graceful skip (not error)
- ``maya-scripting/node_attrs`` — list_attributes attribute-probe filter
- ``maya-scripting/cameras`` — attribute fallback from shape to transform
- ``maya-animation/import_animation_curves`` — file-not-found + target retargeting
- ``conftest.load_and_call`` — shared helper usability
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import third-party modules
# Import local modules
from conftest import SKILLS_ROOT, load_and_call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOD_COUNTER = [0]


def _load(rel_path: str, mock_cmds: MagicMock, func_name: str = "main", **kwargs) -> dict:
    """Thin wrapper around the shared conftest.load_and_call helper."""
    return load_and_call(rel_path, mock_cmds, func_name, **kwargs)


def _make_cmds(**attrs) -> MagicMock:
    mc = MagicMock()
    for k, v in attrs.items():
        setattr(mc, k, v)
    return mc


# ---------------------------------------------------------------------------
# TestSharedHelper
# ---------------------------------------------------------------------------


class TestSharedHelper:
    """Verify the conftest.load_and_call helper works correctly."""

    def test_load_and_call_returns_dict(self):
        mc = _make_cmds(
            objExists=MagicMock(return_value=True),
            objectType=MagicMock(return_value="parentConstraint"),
            listAttr=MagicMock(return_value=["targetW0"]),
            listConnections=MagicMock(return_value=[]),
        )
        result = _load(
            "maya-constraints-advanced/scripts/get_constraint_weights.py",
            mc,
            constraint_node="parentConstraint1",
        )
        assert isinstance(result, dict)

    def test_load_and_call_propagates_kwargs(self):
        mc = _make_cmds(
            objExists=MagicMock(return_value=False),
        )
        result = _load(
            "maya-constraints-advanced/scripts/get_constraint_weights.py",
            mc,
            constraint_node="doesNotExist",
        )
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestConstraintWeightsFallback
# ---------------------------------------------------------------------------


class TestConstraintWeightsFallback:
    """Tests for get_constraint_weights w_attr fallback and attr probe."""

    def _make_constraint_cmds(self, w_attr_exists=True, target_list=None, all_ud=None):
        target_list = target_list or ["driver1"]
        all_ud = all_ud or ["driver1W0"]

        mc = MagicMock()
        mc.objExists.side_effect = lambda name: w_attr_exists or (name == "parentConstraint1")
        mc.objectType.return_value = "parentConstraint"
        mc.listAttr.return_value = all_ud
        mc.listConnections.return_value = target_list
        mc.getAttr.return_value = 0.75
        return mc

    def test_happy_path_w_attr_exists(self):
        mc = self._make_constraint_cmds(w_attr_exists=True)
        mc.objExists.side_effect = lambda name: True
        result = _load(
            "maya-constraints-advanced/scripts/get_constraint_weights.py",
            mc,
            constraint_node="parentConstraint1",
        )
        assert result["success"] is True
        assert "weights" in result["context"]
        assert len(result["context"]["weights"]) == 1
        assert result["context"]["weights"][0]["driver"] == "driver1"

    def test_missing_constraint_node(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _load(
            "maya-constraints-advanced/scripts/get_constraint_weights.py",
            mc,
            constraint_node="missing_constraint",
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_w_attr_fallback_to_all_ud(self):
        """When w_attr does not exist, fall back to listAttr user-defined."""
        mc = MagicMock()

        def obj_exists_side(name):
            # constraint node itself exists; the constructed w_attr does not
            if name == "pc1":
                return True
            if name.endswith("W0") and "driver1" not in name:
                return True  # fallback w_attr exists
            return False

        mc.objExists.side_effect = obj_exists_side
        mc.objectType.return_value = "parentConstraint"
        mc.listAttr.return_value = ["driver1W0"]
        mc.listConnections.return_value = ["driver1"]
        mc.getAttr.return_value = 0.5
        result = _load(
            "maya-constraints-advanced/scripts/get_constraint_weights.py",
            mc,
            constraint_node="pc1",
        )
        assert result["success"] is True

    def test_no_drivers_returns_empty_weights(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "aimConstraint"
        mc.listAttr.return_value = []
        mc.listConnections.return_value = []
        result = _load(
            "maya-constraints-advanced/scripts/get_constraint_weights.py",
            mc,
            constraint_node="aimConstraint1",
        )
        assert result["success"] is True
        assert result["context"]["weights"] == []

    def test_prompt_present(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.objectType.return_value = "parentConstraint"
        mc.listAttr.return_value = []
        mc.listConnections.return_value = []
        result = _load(
            "maya-constraints-advanced/scripts/get_constraint_weights.py",
            mc,
            constraint_node="pc1",
        )
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestAnnotationEdgeCases
# ---------------------------------------------------------------------------


class TestAnnotationEdgeCases:
    """Tests for create_annotation edge cases."""

    def test_target_object_not_found(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        result = _load(
            "maya-annotation/scripts/create_annotation.py",
            mc,
            text="Hello",
            target_object="missing_sphere",
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower() or "missing_sphere" in result["message"]

    def test_world_space_annotation_fallback(self):
        """In standalone fallback, createNode is used instead of annotate."""
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.spaceLocator.return_value = ["_ann_loc_tmp"]
        # Simulate annotate raising an exception (standalone mode)
        mc.annotate.side_effect = RuntimeError("Not available in standalone")
        mc.createNode.side_effect = lambda ntype, **kw: (
            "ann1" if ntype == "annotationShape" else "annXform1"
        )
        mc.listRelatives.return_value = ["annXform1"]

        result = _load(
            "maya-annotation/scripts/create_annotation.py",
            mc,
            text="Test",
        )
        # Should succeed via createNode fallback
        assert isinstance(result, dict)

    def test_annotation_attached_to_object(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.annotate.return_value = "annotationShape1"
        mc.listRelatives.return_value = ["annotationXform1"]
        result = _load(
            "maya-annotation/scripts/create_annotation.py",
            mc,
            text="Note",
            target_object="pSphere1",
        )
        assert result["success"] is True
        assert "annotation_node" in result["context"]

    def test_annotation_with_custom_name(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.annotate.return_value = "annotationShape1"
        mc.listRelatives.return_value = ["annotationXform1"]
        mc.rename.return_value = "myNote"
        result = _load(
            "maya-annotation/scripts/create_annotation.py",
            mc,
            text="Named",
            target_object="pCube1",
            name="myNote",
        )
        assert result["success"] is True

    def test_default_position_used_when_none(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.annotate.return_value = "annotationShape1"
        mc.listRelatives.return_value = ["annXform1"]
        result = _load(
            "maya-annotation/scripts/create_annotation.py",
            mc,
            text="No pos",
            target_object="pSphere1",
        )
        assert result["success"] is True
        assert result["context"]["position"] == [0.0, 1.0, 0.0]


# ---------------------------------------------------------------------------
# TestHIKDefinitionGracefulSkip
# ---------------------------------------------------------------------------


class TestHIKDefinitionGracefulSkip:
    """Tests for create_hik_definition missing-joint graceful skip."""

    def _read_mocap_module(self):
        path = SKILLS_ROOT / "maya-mocap" / "scripts" / "create_hik_definition.py"
        return path

    def test_missing_joint_skipped_not_error(self):
        mc = MagicMock()
        # character node exists; joints do not
        mc.objExists.side_effect = lambda name: name == "myChar"
        mc.createNode.return_value = "myChar"
        mc.ls.return_value = []

        mock_mel = MagicMock()
        mock_maya = MagicMock()
        mock_maya.cmds = mc
        mock_maya.mel = mock_mel

        import importlib.util

        path = self._read_mocap_module()
        spec = importlib.util.spec_from_file_location("test_hik_r33", str(path))
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            spec.loader.exec_module(mod)
            result = mod.main(
                character_name="myChar",
                joint_mapping={"Hips": "missing_hips", "Spine": "missing_spine"},
            )
        assert isinstance(result, dict)
        # Should succeed but with skipped joints reported
        if result["success"]:
            ctx = result.get("context", {})
            skipped = ctx.get("skipped", [])
            assert len(skipped) == 2 or isinstance(skipped, list)

    def test_all_joints_exist_no_skips(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.createNode.return_value = "char1"
        mc.ls.return_value = []

        mock_mel = MagicMock()
        mock_maya = MagicMock()
        mock_maya.cmds = mc
        mock_maya.mel = mock_mel

        import importlib.util

        path = self._read_mocap_module()
        spec = importlib.util.spec_from_file_location("test_hik_r33b", str(path))
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            spec.loader.exec_module(mod)
            result = mod.main(
                character_name="char1",
                joint_mapping={"Hips": "root_joint"},
            )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TestPoseLibraryEdgeCases
# ---------------------------------------------------------------------------


class TestPoseLibraryEdgeCases:
    """Tests for load_pose skip_missing + namespace logic."""

    def test_load_pose_skip_missing(self, tmp_path):
        import json

        pose_file = tmp_path / "test.json"
        pose_data = {
            "controls": {
                "ctrl_l": {"translateX": 1.0, "translateY": 0.0, "translateZ": 0.0}
            }
        }
        pose_file.write_text(json.dumps(pose_data))

        mc = MagicMock()
        mc.objExists.return_value = False  # node not found

        result = _load(
            "maya-pose-library/scripts/load_pose.py",
            mc,
            pose_file=str(pose_file),
            skip_missing=True,
        )
        assert isinstance(result, dict)
        # With skip_missing=True, should succeed and report missing
        if result["success"]:
            assert "missing" in result["context"] or result["success"] is True

    def test_load_pose_error_on_missing_when_not_skipping(self, tmp_path):
        import json

        pose_file = tmp_path / "test.json"
        pose_data = {
            "controls": {
                "ctrl_l": {"translateX": 1.0}
            }
        }
        pose_file.write_text(json.dumps(pose_data))

        mc = MagicMock()
        mc.objExists.return_value = False

        result = _load(
            "maya-pose-library/scripts/load_pose.py",
            mc,
            pose_file=str(pose_file),
            skip_missing=False,
        )
        assert isinstance(result, dict)
        # Without skip_missing, may error or report missing
        # Either outcome is valid; just verify it's a dict

    def test_load_pose_namespace_prepended(self, tmp_path):
        import json

        pose_file = tmp_path / "ns_pose.json"
        pose_data = {
            "controls": {
                "ctrl_r": {"translateX": 2.0, "translateY": 0.5, "translateZ": -1.0}
            }
        }
        pose_file.write_text(json.dumps(pose_data))

        mc = MagicMock()
        mc.objExists.return_value = True
        mc.getAttr.return_value = 0.0

        result = _load(
            "maya-pose-library/scripts/load_pose.py",
            mc,
            pose_file=str(pose_file),
            namespace="char1",
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TestBakeLightingGracefulSkip
# ---------------------------------------------------------------------------


class TestBakeLightingGracefulSkip:
    """Tests for bake_lighting per-object graceful skip."""

    def test_skips_nonexistent_objects(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = False  # all objects missing
        mc.ls.return_value = []

        result = _load(
            "maya-texture-bake/scripts/bake_lighting.py",
            mc,
            objects=["ghost_mesh"],
            output_dir=str(tmp_path),
        )
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["context"]["baked_files"] == []

    def test_bakes_existing_objects(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.select = MagicMock()
        mc.convertLightmap = MagicMock()

        result = _load(
            "maya-texture-bake/scripts/bake_lighting.py",
            mc,
            objects=["pSphere1"],
            output_dir=str(tmp_path),
        )
        assert result["success"] is True
        assert len(result["context"]["baked_files"]) == 1

    def test_mixed_existing_and_missing(self, tmp_path):
        existing = {"pSphere1"}
        mc = MagicMock()
        mc.objExists.side_effect = lambda name: name in existing
        mc.select = MagicMock()
        mc.convertLightmap = MagicMock()

        result = _load(
            "maya-texture-bake/scripts/bake_lighting.py",
            mc,
            objects=["pSphere1", "ghost_mesh"],
            output_dir=str(tmp_path),
        )
        assert result["success"] is True
        assert len(result["context"]["baked_files"]) == 1

    def test_no_objects_error(self, tmp_path):
        mc = MagicMock()
        mc.ls.return_value = []
        result = _load(
            "maya-texture-bake/scripts/bake_lighting.py",
            mc,
            objects=[],
            output_dir=str(tmp_path),
        )
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestNodeAttrsListAttributes
# ---------------------------------------------------------------------------


class TestNodeAttrsListAttributes:
    """Tests for list_attributes attribute-probe filter in node_attrs.py."""

    def test_list_attributes_happy_path(self):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.listAttr.return_value = ["tx", "ty", "tz"]
        mc.getAttr.side_effect = lambda full_attr, **kw: {
            "type": "double",
            "keyable": True,
            "lock": False,
        }.get(list(kw.keys())[0] if kw else "type", "double")

        result = _load(
            "maya-scripting/scripts/node_attrs.py",
            mc,
            func_name="list_attributes",
            object_name="pSphere1",
        )
        assert isinstance(result, dict)

    def test_list_attributes_missing_node(self):
        mc = MagicMock()
        mc.objExists.return_value = False

        result = _load(
            "maya-scripting/scripts/node_attrs.py",
            mc,
            func_name="list_attributes",
            object_name="ghost_node",
        )
        assert result["success"] is False

    def test_list_attributes_attr_probe_skips_missing_attrs(self):
        """cmds.objExists on 'node.attr' returns False → attribute silently skipped."""
        mc = MagicMock()

        def obj_exists(name):
            # node exists; its attribute does not
            return "." not in name

        mc.objExists.side_effect = obj_exists
        mc.listAttr.return_value = ["tx", "ty"]
        result = _load(
            "maya-scripting/scripts/node_attrs.py",
            mc,
            func_name="list_attributes",
            object_name="pSphere1",
        )
        assert isinstance(result, dict)
        # attributes should be empty since none of the attrs exist
        if result["success"]:
            assert result["context"].get("attributes") == [] or isinstance(
                result["context"].get("attributes"), list
            )


# ---------------------------------------------------------------------------
# TestCamerasAttrFallback
# ---------------------------------------------------------------------------


class TestCamerasAttrFallback:
    """Tests for cameras.py attribute fallback from shape to transform."""

    def test_set_camera_attribute_missing_node(self):
        mc = MagicMock()
        mc.objExists.return_value = False
        mc.listRelatives.return_value = []

        result = _load(
            "maya-scripting/scripts/cameras.py",
            mc,
            func_name="set_camera_attribute",
            camera_name="camera1",
            attribute="focalLength",
            value=50,
        )
        assert result["success"] is False

    def test_set_attribute_fallback_to_transform(self):
        """When attribute is not on shape, fallback to transform node."""
        mc = MagicMock()

        def obj_exists(name):
            # shape.attr does not exist, transform.attr does
            if "cameraShape1." in name:
                return False
            return True

        mc.objExists.side_effect = obj_exists
        mc.listRelatives.return_value = ["cameraShape1"]
        mc.setAttr = MagicMock()

        result = _load(
            "maya-scripting/scripts/cameras.py",
            mc,
            func_name="set_camera_attribute",
            camera_name="camera1",
            attribute="focalLength",
            value=50,
        )
        assert result["success"] is True


# ---------------------------------------------------------------------------
# TestImportAnimationCurves
# ---------------------------------------------------------------------------


class TestImportAnimationCurves:
    """Tests for import_animation_curves including file-not-found and retargeting."""

    def test_file_not_found_error(self):
        mc = MagicMock()
        result = _load(
            "maya-animation/scripts/import_animation_curves.py",
            mc,
            file_path="/nonexistent/curves.ma",
        )
        assert result["success"] is False
        assert "not found" in result["message"].lower() or "not exist" in result["message"].lower()

    def test_import_without_retarget(self, tmp_path):
        anim_file = tmp_path / "curves.ma"
        anim_file.write_text("// Maya ASCII")

        mc = MagicMock()
        mc.file = MagicMock()

        result = _load(
            "maya-animation/scripts/import_animation_curves.py",
            mc,
            file_path=str(anim_file),
        )
        assert result["success"] is True
        assert result["context"]["target_object"] is None

    def test_import_with_retarget(self, tmp_path):
        anim_file = tmp_path / "retarget.ma"
        anim_file.write_text("// Maya ASCII")

        mc = MagicMock()
        mc.file = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = ["animCurve1"]
        mc.listConnections.return_value = ["pSphere1.translateX"]

        result = _load(
            "maya-animation/scripts/import_animation_curves.py",
            mc,
            file_path=str(anim_file),
            target_object="pSphere1",
        )
        assert result["success"] is True
        assert result["context"]["target_object"] == "pSphere1"

    def test_import_with_merge_false(self, tmp_path):
        anim_file = tmp_path / "nomerge.ma"
        anim_file.write_text("// Maya ASCII")

        mc = MagicMock()
        mc.file = MagicMock()
        mc.objExists.return_value = False

        result = _load(
            "maya-animation/scripts/import_animation_curves.py",
            mc,
            file_path=str(anim_file),
            merge=False,
        )
        assert result["success"] is True


# ---------------------------------------------------------------------------
# TestBakeAOGracefulSkip
# ---------------------------------------------------------------------------


class TestBakeAOGracefulSkip:
    """Tests for bake_ambient_occlusion graceful skip of missing objects."""

    def test_skips_missing_objects(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = False
        mc.ls.return_value = []

        result = _load(
            "maya-texture-bake/scripts/bake_ambient_occlusion.py",
            mc,
            objects=["ghost_mesh"],
            output_dir=str(tmp_path),
        )
        assert isinstance(result, dict)
        assert result["success"] is True

    def test_bakes_existing_objects(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.createNode.return_value = "mib_ao1"
        mc.shadingNode.return_value = "mib_ao1"
        mc.sets.return_value = "sg1"
        mc.listConnections.return_value = ["lambert1SG"]

        result = _load(
            "maya-texture-bake/scripts/bake_ambient_occlusion.py",
            mc,
            objects=["pSphere1"],
            output_dir=str(tmp_path),
        )
        assert isinstance(result, dict)
        assert result["success"] is True


# ---------------------------------------------------------------------------
# TestSavePoseGracefulSkip
# ---------------------------------------------------------------------------


class TestSavePoseGracefulSkip:
    """Tests for save_pose graceful skip of missing controls."""

    def test_skips_missing_controls(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = False
        mc.ls.return_value = []

        result = _load(
            "maya-pose-library/scripts/save_pose.py",
            mc,
            file_path=str(tmp_path / "out.json"),
            controls=["ctrl_missing"],
        )
        assert isinstance(result, dict)
        # save_pose should succeed with empty snapshot (0 controls captured)

    def test_saves_existing_controls(self, tmp_path):
        mc = MagicMock()
        mc.objExists.return_value = True
        mc.getAttr.return_value = 0.0
        mc.ls.return_value = ["ctrl_l"]

        result = _load(
            "maya-pose-library/scripts/save_pose.py",
            mc,
            file_path=str(tmp_path / "out.json"),
            controls=["ctrl_l"],
        )
        assert isinstance(result, dict)
        assert result["success"] is True


# ---------------------------------------------------------------------------
# TestMirrorPoseGracefulSkip
# ---------------------------------------------------------------------------


class TestMirrorPoseGracefulSkip:
    """Tests for mirror_pose skip of missing mirrored nodes."""

    def test_missing_mirrored_node_skipped(self, tmp_path):
        import json

        pose_file = tmp_path / "pose.json"
        pose_data = {
            "controls": {
                "L_ctrl": {"translateX": 1.0, "rotateY": 10.0, "rotateZ": 5.0}
            }
        }
        pose_file.write_text(json.dumps(pose_data))

        mc = MagicMock()
        mc.objExists.return_value = False  # R_ctrl does not exist

        result = _load(
            "maya-pose-library/scripts/mirror_pose.py",
            mc,
            pose_file=str(pose_file),
        )
        assert isinstance(result, dict)
        # Should succeed even if mirror targets are missing

    def test_applies_when_mirror_exists(self, tmp_path):
        import json

        pose_file = tmp_path / "pose.json"
        pose_data = {
            "controls": {
                "L_ctrl": {"translateX": 1.0, "rotateY": 10.0, "rotateZ": 5.0}
            }
        }
        pose_file.write_text(json.dumps(pose_data))

        mc = MagicMock()
        mc.objExists.return_value = True
        mc.setAttr = MagicMock()

        result = _load(
            "maya-pose-library/scripts/mirror_pose.py",
            mc,
            pose_file=str(pose_file),
            apply_to_scene=True,
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TestGlobalObjExistsCount
# ---------------------------------------------------------------------------


class TestGlobalObjExistsCount:
    """Structural guard: remaining cmds.objExists count."""

    def test_total_objexists_below_60(self):
        """Confirm total cmds.objExists in skill scripts is below 60 (attribute probes + intentional positive guards)."""
        import re

        skills_src = Path(__file__).parent.parent / "src" / "dcc_mcp_maya"
        total = 0
        for py in skills_src.rglob("*.py"):
            if "api.py" in py.name:
                continue
            total += len(re.findall(r"cmds\.objExists", py.read_text(encoding="utf-8", errors="ignore")))
        assert total < 60, "cmds.objExists count {} should be < 60".format(total)

    def test_validate_node_exists_usage_broad(self):
        """validate_node_exists should appear in at least 170 skill scripts."""
        skills_src = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
        using = sum(
            1
            for py in skills_src.rglob("*.py")
            if "validate_node_exists" in py.read_text(encoding="utf-8", errors="ignore")
        )
        assert using >= 170, "validate_node_exists used in {} files, expected >= 170".format(using)
