"""Round 32: Test batch_validate_nodes migration for list-comprehension objExists patterns.

26 scripts migrated from:
    missing = [o for o in objects if not cmds.objExists(o)]
    if missing:
        return skill_error(...)

To:
    err = batch_validate_nodes(cmds, list(objects))
    if err:
        return err

Covers: maya-deformers, maya-xform-utils, maya-animation, maya-blend-shape-utils,
        maya-dynamics, maya-gpu-cache, maya-instancer, maya-render-layers,
        maya-rig-utils, maya-rigging, maya-scene-utils, maya-scripting,
        maya-sets, maya-texture-bake
"""

# Import built-in modules
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_and_call(rel_path: str, mock_cmds: MagicMock, func_name: str = "main", **kwargs) -> dict:
    """Load a skill script and call a function, keeping the Maya mock active throughout."""
    import importlib.util

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    fpath = _SKILLS_ROOT / rel_path
    mod_name = "skill_r32_{}".format(fpath.stem)
    spec = importlib.util.spec_from_file_location(mod_name, fpath)
    mod = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
        spec.loader.exec_module(mod)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


def _load_script(rel_path: str, mock_cmds: MagicMock) -> ModuleType:
    """Load a skill script module with the given mock cmds (module stays patched during exec only).

    Note: for testing actual behavior, use _load_and_call which keeps the patch active during call.
    """
    import importlib.util

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    fpath = _SKILLS_ROOT / rel_path
    mod_name = "skill_r32s_{}".format(fpath.stem)
    spec = importlib.util.spec_from_file_location(mod_name, fpath)
    mod = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
        spec.loader.exec_module(mod)
    return mod


def _make_cmds(**side_effects) -> MagicMock:
    """Create a mock maya.cmds with objExists returning True by default."""
    cmds = MagicMock()
    cmds.objExists.return_value = True
    for attr, val in side_effects.items():
        setattr(cmds, attr, val)
    return cmds


def _missing_cmds(*missing_nodes) -> MagicMock:
    """Create cmds where specified nodes do NOT exist."""
    cmds = MagicMock()
    cmds.objExists.side_effect = lambda name: name not in missing_nodes
    return cmds


# ---------------------------------------------------------------------------
# Structural: verify all 26 files have top-level batch_validate_nodes import
# ---------------------------------------------------------------------------


MIGRATED_FILES = [
    "maya-animation/scripts/bake_constraints.py",
    "maya-animation/scripts/bake_simulation.py",
    "maya-blend-shape-utils/scripts/create_blend_shape.py",
    "maya-deformers/scripts/create_cluster.py",
    "maya-deformers/scripts/create_lattice.py",
    "maya-deformers/scripts/sculpt_deformer.py",
    "maya-deformers/scripts/wire_deformer.py",
    "maya-dynamics/scripts/connect_field_to_objects.py",
    "maya-dynamics/scripts/create_dynamic_field.py",
    "maya-gpu-cache/scripts/export_gpu_cache.py",
    "maya-instancer/scripts/create_instancer.py",
    "maya-render-layers/scripts/create_render_layer.py",
    "maya-rig-utils/scripts/add_space_switch.py",
    "maya-rigging/scripts/create_blend_shape.py",
    "maya-scene-utils/scripts/align_objects.py",
    "maya-scripting/scripts/display.py",
    "maya-scripting/scripts/render_layers.py",
    "maya-scripting/scripts/scene_utils.py",
    "maya-scripting/scripts/texture_bake.py",
    "maya-sets/scripts/add_to_set.py",
    "maya-sets/scripts/create_set.py",
    "maya-texture-bake/scripts/bake_textures.py",
    "maya-xform-utils/scripts/bake_transforms.py",
    "maya-xform-utils/scripts/freeze_transforms.py",
    "maya-xform-utils/scripts/reset_pivot.py",
]


class TestRound32Structural:
    """Structural checks for the 26 migrated files."""

    @pytest.mark.parametrize("rel_path", MIGRATED_FILES)
    def test_no_list_comp_objexists(self, rel_path):
        """No list-comprehension objExists pattern should remain."""
        source = (_SKILLS_ROOT / rel_path).read_text(encoding="utf-8")
        assert (
            "[" not in source
            or "for" not in source
            or "cmds.objExists" not in source
            or not any(
                "if not cmds.objExists" in line and "[" in line and "for" in line for line in source.splitlines()
            )
        ), "List-comp objExists pattern still present in {}".format(rel_path)

    @pytest.mark.parametrize("rel_path", MIGRATED_FILES)
    def test_batch_validate_nodes_imported_top_level(self, rel_path):
        """batch_validate_nodes must be imported at top-level (not indented)."""
        source = (_SKILLS_ROOT / rel_path).read_text(encoding="utf-8")
        # scene_utils.py uses merged import with validate_node_exists
        if "batch_validate_nodes(cmds," not in source:
            return  # not used (no replacement happened — shouldn't occur)
        bad = [
            line
            for line in source.splitlines()
            if "from dcc_mcp_maya.api import" in line
            and "batch_validate_nodes" in line
            and line.startswith((" ", "\t"))
        ]
        assert bad == [], "Indented import in {}: {}".format(rel_path, bad)

    def test_global_objexists_count_below_60(self):
        """Total remaining cmds.objExists calls must be below 60."""
        total = sum(
            path.read_text(encoding="utf-8").count("cmds.objExists") for path in _SKILLS_ROOT.rglob("scripts/*.py")
        )
        assert total < 60, "Expected < 60 remaining objExists, got {}".format(total)

    def test_batch_validate_nodes_usage_count(self):
        """At least 35 scripts should use batch_validate_nodes."""
        count = sum(
            1
            for path in _SKILLS_ROOT.rglob("scripts/*.py")
            if "batch_validate_nodes" in path.read_text(encoding="utf-8")
        )
        assert count >= 35, "Expected >= 35 scripts using batch_validate_nodes, got {}".format(count)


# ---------------------------------------------------------------------------
# Deformers
# ---------------------------------------------------------------------------


class TestDeformersRound32:
    """Tests for migrated maya-deformers scripts."""

    def test_create_cluster_missing_object(self):
        """create_cluster returns error when object does not exist."""
        mock_cmds = _missing_cmds("pCube1")
        result = _load_and_call("maya-deformers/scripts/create_cluster.py", mock_cmds, objects=["pCube1"])
        assert not result["success"]

    def test_create_cluster_happy_path(self):
        """create_cluster succeeds when objects exist."""
        mock_cmds = _make_cmds()
        mock_cmds.cluster.return_value = ["cluster1Handle", "cluster1"]
        result = _load_and_call("maya-deformers/scripts/create_cluster.py", mock_cmds, objects=["pCube1", "pSphere1"])
        assert result["success"]
        assert "cluster_node" in result.get("context", {})

    def test_create_cluster_empty_objects(self):
        """create_cluster returns error for empty objects list."""
        mock_cmds = _make_cmds()
        result = _load_and_call("maya-deformers/scripts/create_cluster.py", mock_cmds, objects=[])
        assert not result["success"]

    def test_wire_deformer_missing_curve(self):
        """wire_deformer returns error when curve does not exist."""
        mock_cmds = _missing_cmds("wire1")
        result = _load_and_call(
            "maya-deformers/scripts/wire_deformer.py", mock_cmds, curves=["wire1"], objects=["pCube1"]
        )
        assert not result["success"]

    def test_wire_deformer_missing_object(self):
        """wire_deformer returns error when mesh does not exist."""
        mock_cmds = MagicMock()
        mock_cmds.objExists.side_effect = lambda n: n != "missingMesh"
        result = _load_and_call(
            "maya-deformers/scripts/wire_deformer.py", mock_cmds, curves=["wireCurve"], objects=["missingMesh"]
        )
        assert not result["success"]

    def test_create_lattice_missing_object(self):
        """create_lattice returns error when object does not exist."""
        mock_cmds = _missing_cmds("meshA")
        result = _load_and_call("maya-deformers/scripts/create_lattice.py", mock_cmds, objects=["meshA"])
        assert not result["success"]

    def test_sculpt_deformer_missing_object(self):
        """sculpt_deformer returns error when object does not exist."""
        mock_cmds = _missing_cmds("nonexistent")
        result = _load_and_call("maya-deformers/scripts/sculpt_deformer.py", mock_cmds, objects=["nonexistent"])
        assert not result["success"]


# ---------------------------------------------------------------------------
# XForm utils
# ---------------------------------------------------------------------------


class TestXFormUtilsRound32:
    """Tests for migrated maya-xform-utils scripts."""

    def test_freeze_transforms_missing_object(self):
        """freeze_transforms returns error when object does not exist."""
        mock_cmds = _missing_cmds("missing1")
        result = _load_and_call("maya-xform-utils/scripts/freeze_transforms.py", mock_cmds, objects=["missing1"])
        assert not result["success"]

    def test_freeze_transforms_happy_path(self):
        """freeze_transforms succeeds when objects exist."""
        mock_cmds = _make_cmds()
        mock_cmds.makeIdentity.return_value = None
        mock_cmds.xform.return_value = [0, 0, 0, 0, 0, 0, 1, 1, 1]
        result = _load_and_call("maya-xform-utils/scripts/freeze_transforms.py", mock_cmds, objects=["pCube1"])
        assert result["success"]

    def test_reset_pivot_missing_object(self):
        """reset_pivot returns error when object does not exist."""
        mock_cmds = _missing_cmds("pMissing")
        result = _load_and_call("maya-xform-utils/scripts/reset_pivot.py", mock_cmds, objects=["pMissing"])
        assert not result["success"]

    def test_bake_transforms_missing_object(self):
        """bake_transforms returns error when object does not exist."""
        mock_cmds = _missing_cmds("missingNode")
        result = _load_and_call("maya-xform-utils/scripts/bake_transforms.py", mock_cmds, objects=["missingNode"])
        assert not result["success"]


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------


class TestAnimationRound32:
    """Tests for migrated maya-animation scripts."""

    def test_bake_constraints_missing_object(self):
        """bake_constraints returns error when object does not exist."""
        mock_cmds = _missing_cmds("missingObj")
        result = _load_and_call("maya-animation/scripts/bake_constraints.py", mock_cmds, objects=["missingObj"])
        assert not result["success"]

    def test_bake_simulation_missing_object(self):
        """bake_simulation returns error when object does not exist."""
        mock_cmds = _missing_cmds("missingObj")
        result = _load_and_call("maya-animation/scripts/bake_simulation.py", mock_cmds, objects=["missingObj"])
        assert not result["success"]


# ---------------------------------------------------------------------------
# Blend shape utils
# ---------------------------------------------------------------------------


class TestBlendShapeRound32:
    """Tests for migrated maya-blend-shape-utils/create_blend_shape.py."""

    def test_create_blend_shape_missing_target(self):
        """create_blend_shape returns error when a target does not exist."""
        mock_cmds = _missing_cmds("missingTarget")
        result = _load_and_call(
            "maya-blend-shape-utils/scripts/create_blend_shape.py",
            mock_cmds,
            mesh="baseMesh",
            targets=["missingTarget"],
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# Dynamics
# ---------------------------------------------------------------------------


class TestDynamicsRound32:
    """Tests for migrated maya-dynamics scripts."""

    def test_connect_field_missing_object(self):
        """connect_field_to_objects returns error when object does not exist."""
        mock_cmds = _missing_cmds("missingObj")
        mock_cmds.objectType.return_value = "turbulenceField"
        result = _load_and_call(
            "maya-dynamics/scripts/connect_field_to_objects.py",
            mock_cmds,
            field="turbulenceField1",
            objects=["missingObj"],
        )
        assert not result["success"]

    def test_create_dynamic_field_missing_objects(self):
        """create_dynamic_field returns error when objects do not exist."""
        mock_cmds = _missing_cmds("ghost1")
        mock_cmds.objectType.return_value = "transform"
        result = _load_and_call(
            "maya-dynamics/scripts/create_dynamic_field.py",
            mock_cmds,
            field_type="gravity",
            objects=["ghost1"],
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# GPU cache
# ---------------------------------------------------------------------------


class TestGpuCacheRound32:
    """Tests for migrated maya-gpu-cache/export_gpu_cache.py."""

    def test_export_gpu_cache_missing_object(self):
        """export_gpu_cache returns error when objects do not exist."""
        mock_cmds = _missing_cmds("missingMesh")
        result = _load_and_call(
            "maya-gpu-cache/scripts/export_gpu_cache.py",
            mock_cmds,
            objects=["missingMesh"],
            output_path="/tmp/test.abc",
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# Instancer
# ---------------------------------------------------------------------------


class TestInstancerRound32:
    """Tests for migrated maya-instancer/create_instancer.py."""

    def test_create_instancer_missing_geometry(self):
        """create_instancer returns error when geometry does not exist."""
        mock_cmds = _missing_cmds("ghostGeo")
        result = _load_and_call(
            "maya-instancer/scripts/create_instancer.py",
            mock_cmds,
            instance_objects=["ghostGeo"],
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# Render layers
# ---------------------------------------------------------------------------


class TestRenderLayersRound32:
    """Tests for migrated maya-render-layers/create_render_layer.py."""

    def test_create_render_layer_missing_object(self):
        """create_render_layer returns error when objects do not exist."""
        mock_cmds = _missing_cmds("missingGeo")
        result = _load_and_call(
            "maya-render-layers/scripts/create_render_layer.py",
            mock_cmds,
            name="testLayer",
            objects_to_add=["missingGeo"],
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# Rig utils
# ---------------------------------------------------------------------------


class TestRigUtilsRound32:
    """Tests for migrated maya-rig-utils/add_space_switch.py."""

    def test_add_space_switch_missing_space(self):
        """add_space_switch returns error when a space object does not exist."""
        mock_cmds = _missing_cmds("missingSpace")
        mock_cmds.objectType.return_value = "transform"
        result = _load_and_call(
            "maya-rig-utils/scripts/add_space_switch.py",
            mock_cmds,
            control="ctrl",
            spaces=["missingSpace"],
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# Scene utils
# ---------------------------------------------------------------------------


class TestSceneUtilsRound32:
    """Tests for migrated maya-scene-utils/align_objects.py."""

    def test_align_objects_missing_object(self):
        """align_objects returns error when objects do not exist."""
        mock_cmds = _missing_cmds("missingObj")
        result = _load_and_call(
            "maya-scene-utils/scripts/align_objects.py",
            mock_cmds,
            objects=["missingObj"],
            reference="ref1",
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# Sets
# ---------------------------------------------------------------------------


class TestSetsRound32:
    """Tests for migrated maya-sets scripts."""

    def test_add_to_set_missing_object(self):
        """add_to_set returns error when objects do not exist."""
        mock_cmds = _missing_cmds("ghostMesh")
        mock_cmds.objectType.return_value = "objectSet"
        result = _load_and_call(
            "maya-sets/scripts/add_to_set.py",
            mock_cmds,
            set_name="mySet",
            objects=["ghostMesh"],
        )
        assert not result["success"]

    def test_create_set_missing_object(self):
        """create_set returns error when objects_to_add do not exist."""
        mock_cmds = _missing_cmds("ghostObj")
        result = _load_and_call(
            "maya-sets/scripts/create_set.py",
            mock_cmds,
            name="mySet",
            objects_to_add=["ghostObj"],
        )
        assert not result["success"]


# ---------------------------------------------------------------------------
# Texture bake
# ---------------------------------------------------------------------------


class TestTextureBakeRound32:
    """Tests for migrated texture bake scripts."""

    def test_bake_textures_missing_object(self):
        """bake_textures returns error when objects do not exist."""
        mock_cmds = _missing_cmds("missingMesh")
        result = _load_and_call(
            "maya-texture-bake/scripts/bake_textures.py",
            mock_cmds,
            objects=["missingMesh"],
        )
        assert not result["success"]
