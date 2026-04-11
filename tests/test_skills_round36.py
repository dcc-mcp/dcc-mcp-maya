"""Round-36 deep edge-case tests for maya-nparticles, maya-fluid, and maya-constraints.

Uses conftest.load_and_call / load_and_call_with_mel to test complex branches:
- nParticle emitter creation with mel mocking, no-shape fallback, nucleus selection
- nParticle attribute validation (wrong type, missing attr, happy path)
- add_field_to_nparticles: unknown field, no particles, auto-target, rename fallback
- list_nparticle_systems: empty, two shapes + two nuclei, getAttr exceptions
- Fluid container: create with/without name, no shape fallback, list (resolution), delete missing
- set_fluid_attribute: missing node, happy path
- add_constraint / create_constraint_weighted: unknown type, missing nodes, happy path
- list_constraints: missing node, no constraints, two types found
- remove_constraint: missing node, no constraints, specific type removal
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock

# Import third-party modules
import pytest

from conftest import SKILLS_ROOT, load_and_call, load_and_call_with_mel  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _call(rel, mock_cmds, **kw):
    return load_and_call(rel, mock_cmds, **kw)


def _call_mel(rel, mock_cmds, mock_mel=None, **kw):
    return load_and_call_with_mel(rel, mock_cmds, mock_mel=mock_mel, **kw)


def _nparticle(script):
    return "maya-nparticles/scripts/{}.py".format(script)


def _fluid(script):
    return "maya-fluid/scripts/{}.py".format(script)


def _constraint(script):
    return "maya-constraints/scripts/{}.py".format(script)


# ===========================================================================
# nParticles
# ===========================================================================


class TestCreateNParticleEmitter:
    def test_happy_path(self):
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        # After mel.eval, ls returns a shape
        mock_cmds.ls.side_effect = [
            ["nParticle1Shape"],  # ls(type="nParticle")
            ["nucleus1"],         # ls(type="nucleus") inside actual_nucleus logic
        ]
        mock_cmds.listConnections.return_value = ["emitter1"]
        mock_cmds.listRelatives.side_effect = [
            ["nParticle1"],            # parent of shape
            ["nParticle1Shape"],       # shapes after rename
        ]
        mock_cmds.rename.return_value = "myParticle"
        result = _call_mel(
            _nparticle("create_nparticle_emitter"),
            mock_cmds,
            mock_mel=mock_mel,
            name="myParticle",
            emitter_type="omni",
            rate=200.0,
            speed=2.0,
        )
        assert result["success"] is True
        assert "particle_shape" in result["context"]
        assert result["context"]["rate"] == 200.0

    def test_no_particle_shape_after_creation(self):
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        mock_cmds.ls.return_value = []  # no nParticle shapes
        result = _call_mel(
            _nparticle("create_nparticle_emitter"),
            mock_cmds,
            mock_mel=mock_mel,
        )
        assert result["success"] is False
        assert "nParticle" in result["message"]

    def test_no_emitter_connected(self):
        """When listConnections returns empty, emitter is None — still succeeds."""
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        mock_cmds.ls.side_effect = [["nParticle1Shape"], []]
        mock_cmds.listConnections.return_value = []  # no emitter
        mock_cmds.listRelatives.side_effect = [
            ["nParticle1"],
            ["nParticle1Shape"],
        ]
        mock_cmds.rename.return_value = "nParticle1"
        result = _call_mel(_nparticle("create_nparticle_emitter"), mock_cmds, mock_mel=mock_mel)
        assert result["success"] is True
        assert result["context"]["emitter"] is None

    def test_rename_exception_gracefully_ignored(self):
        """Rename raising exception should not break creation."""
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        mock_cmds.ls.side_effect = [["nParticle1Shape"], []]
        mock_cmds.listConnections.return_value = ["emitter1"]
        mock_cmds.listRelatives.return_value = ["nParticle1"]
        mock_cmds.rename.side_effect = RuntimeError("rename failed")
        result = _call_mel(_nparticle("create_nparticle_emitter"), mock_cmds, mock_mel=mock_mel)
        assert result["success"] is True

    def test_existing_nucleus_used_when_specified(self):
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        mock_cmds.ls.side_effect = [["pShape"], ["nucleus1", "nucleus2"]]
        mock_cmds.listConnections.return_value = []
        mock_cmds.listRelatives.return_value = ["pTransform"]
        mock_cmds.rename.return_value = "pTransform"
        mock_cmds.objExists.return_value = True  # provided nucleus exists
        result = _call_mel(
            _nparticle("create_nparticle_emitter"),
            mock_cmds,
            mock_mel=mock_mel,
            nucleus="nucleus1",
        )
        assert result["success"] is True
        assert result["context"]["nucleus"] == "nucleus1"

    def test_nucleus_fallback_to_last_when_not_found(self):
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        mock_cmds.ls.side_effect = [["pShape"], ["nucleus1", "nucleus2"]]
        mock_cmds.listConnections.return_value = []
        mock_cmds.listRelatives.return_value = ["pTransform"]
        mock_cmds.rename.return_value = "pTransform"
        mock_cmds.objExists.return_value = False  # nucleus doesn't exist
        result = _call_mel(
            _nparticle("create_nparticle_emitter"),
            mock_cmds,
            mock_mel=mock_mel,
            nucleus="badNucleus",
        )
        assert result["success"] is True
        assert result["context"]["nucleus"] == "nucleus2"

    def test_directional_emitter_type_index(self):
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        mock_cmds.ls.side_effect = [["pShape"], []]
        mock_cmds.listConnections.return_value = ["emitter1"]
        mock_cmds.listRelatives.side_effect = [["pT"], ["pShape"]]
        mock_cmds.rename.return_value = "pT"
        result = _call_mel(
            _nparticle("create_nparticle_emitter"),
            mock_cmds,
            mock_mel=mock_mel,
            emitter_type="directional",
        )
        assert result["success"] is True
        # setAttr called with emitterType = 1
        calls = [str(c) for c in mock_cmds.setAttr.call_args_list]
        assert any("emitterType" in c and "1" in c for c in calls)

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_mel = MagicMock()
        mock_cmds.ls.side_effect = [["pShape"], []]
        mock_cmds.listConnections.return_value = []
        mock_cmds.listRelatives.return_value = ["pT"]
        mock_cmds.rename.return_value = "pT"
        result = _call_mel(_nparticle("create_nparticle_emitter"), mock_cmds, mock_mel=mock_mel)
        assert result["success"] is True
        assert result.get("prompt")


class TestSetNParticleAttribute:
    def test_missing_node(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = False
        result = _call(_nparticle("set_nparticle_attribute"), mock_cmds,
                       particle_shape="bad", attribute="radius", value=0.5)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_wrong_node_type(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "mesh"  # not nParticle
        result = _call(_nparticle("set_nparticle_attribute"), mock_cmds,
                       particle_shape="meshNode", attribute="radius", value=0.5)
        assert result["success"] is False
        assert "nParticle" in result["message"]

    def test_missing_attribute(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "nParticle"
        mock_cmds.attributeQuery.return_value = False  # attr doesn't exist
        result = _call(_nparticle("set_nparticle_attribute"), mock_cmds,
                       particle_shape="nParticle1", attribute="badAttr", value=1.0)
        assert result["success"] is False
        assert "badAttr" in result["message"]

    def test_happy_path(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "nParticle"
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 0.5
        result = _call(_nparticle("set_nparticle_attribute"), mock_cmds,
                       particle_shape="nParticle1", attribute="radius", value=0.5)
        assert result["success"] is True
        assert result["context"]["value"] == 0.5

    def test_context_keys(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "nParticle"
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 3.14
        result = _call(_nparticle("set_nparticle_attribute"), mock_cmds,
                       particle_shape="pShape", attribute="drag", value=3.14)
        assert result["context"]["particle_shape"] == "pShape"
        assert result["context"]["attribute"] == "drag"
        assert result.get("prompt")


class TestAddFieldToNParticles:
    def test_unknown_field_type(self):
        mock_cmds = MagicMock()
        result = _call(_nparticle("add_field_to_nparticles"), mock_cmds,
                       field_type="unknownField")
        assert result["success"] is False
        assert "Unknown field type" in result["message"]

    def test_no_nparticle_shapes_and_none_provided(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = []  # no shapes in scene
        result = _call(_nparticle("add_field_to_nparticles"), mock_cmds,
                       field_type="gravity", particle_shapes=None)
        assert result["success"] is False
        assert "No nParticle" in result["message"]

    def test_happy_path_with_explicit_shapes(self):
        mock_cmds = MagicMock()
        mock_cmds.gravity = MagicMock(return_value=["gravityField1"])
        mock_cmds.listRelatives.return_value = ["gravityShape1"]
        result = _call(_nparticle("add_field_to_nparticles"), mock_cmds,
                       field_type="gravity", particle_shapes=["pShape1", "pShape2"],
                       magnitude=9.8)
        assert result["success"] is True
        assert result["context"]["field_type"] == "gravity"
        assert len(result["context"]["connected_particles"]) == 2

    def test_auto_target_all_particles_in_scene(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = ["pShape1", "pShape2", "pShape3"]
        mock_cmds.turbulence = MagicMock(return_value=["turbField1"])
        mock_cmds.listRelatives.return_value = ["turbShape1"]
        result = _call(_nparticle("add_field_to_nparticles"), mock_cmds,
                       field_type="turbulence", particle_shapes=None)
        assert result["success"] is True
        assert len(result["context"]["connected_particles"]) == 3

    def test_rename_field(self):
        mock_cmds = MagicMock()
        mock_cmds.drag = MagicMock(return_value=["dragField1"])
        mock_cmds.rename.return_value = "myDragField"
        mock_cmds.listRelatives.return_value = []
        result = _call(_nparticle("add_field_to_nparticles"), mock_cmds,
                       field_type="drag", particle_shapes=["pShape1"],
                       field_name="myDragField")
        assert result["success"] is True
        assert result["context"]["field_transform"] == "myDragField"

    def test_rename_exception_ignored(self):
        mock_cmds = MagicMock()
        mock_cmds.newton = MagicMock(return_value=["newtonField1"])
        mock_cmds.rename.side_effect = RuntimeError("locked")
        mock_cmds.listRelatives.return_value = []
        result = _call(_nparticle("add_field_to_nparticles"), mock_cmds,
                       field_type="newton", particle_shapes=["pShape1"],
                       field_name="myField")
        assert result["success"] is True  # rename failure should not fail the skill

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.gravity = MagicMock(return_value=["g1"])
        mock_cmds.listRelatives.return_value = []
        result = _call(_nparticle("add_field_to_nparticles"), mock_cmds,
                       field_type="gravity", particle_shapes=["p1"])
        assert result.get("prompt")


class TestListNParticleSystems:
    def test_empty_scene(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.side_effect = [[], []]  # no shapes, no nuclei
        result = _call(_nparticle("list_nparticle_systems"), mock_cmds)
        assert result["success"] is True
        assert result["context"]["system_count"] == 0
        assert result["context"]["systems"] == []
        assert result["context"]["nucleus_solvers"] == []

    def test_two_shapes_two_nuclei(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.side_effect = [
            ["nParticle1Shape", "nParticle2Shape"],
            ["nucleus1", "nucleus2"],
        ]
        mock_cmds.nParticle.return_value = 50
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 0.1
        mock_cmds.listConnections.side_effect = [
            ["nucleus1"],   # nParticle1Shape → nucleus
            ["emitter1"],   # nParticle1Shape → emitters
            ["nucleus2"],   # nParticle2Shape → nucleus
            [],             # nParticle2Shape → emitters
        ]
        result = _call(_nparticle("list_nparticle_systems"), mock_cmds)
        assert result["success"] is True
        assert result["context"]["system_count"] == 2
        assert len(result["context"]["nucleus_solvers"]) == 2

    def test_getattr_exception_gracefully_handled(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.side_effect = [["pShape"], ["nuc1"]]
        mock_cmds.nParticle.side_effect = RuntimeError("no count")
        mock_cmds.attributeQuery.return_value = False
        mock_cmds.listConnections.side_effect = [
            RuntimeError("conn error"),
            RuntimeError("conn error"),
        ]
        mock_cmds.getAttr.side_effect = RuntimeError("no attr")
        result = _call(_nparticle("list_nparticle_systems"), mock_cmds)
        assert result["success"] is True
        assert result["context"]["systems"][0]["count"] == 0
        assert result["context"]["systems"][0]["radius"] is None

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.side_effect = [[], []]
        result = _call(_nparticle("list_nparticle_systems"), mock_cmds)
        assert result.get("prompt")


# ===========================================================================
# Fluid
# ===========================================================================


class TestCreateFluidContainer:
    def test_happy_path_with_name(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.side_effect = [
            ["fluid1"],         # parent of shape
            ["fluidShape1b"],   # shapes after rename
        ]
        mock_cmds.rename.return_value = "myFluid"
        result = _call(_fluid("create_fluid_container"), mock_cmds,
                       name="myFluid", size_x=5.0, size_y=5.0, size_z=5.0, resolution=8)
        assert result["success"] is True
        assert result["context"]["fluid_transform"] == "myFluid"

    def test_happy_path_without_name(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        result = _call(_fluid("create_fluid_container"), mock_cmds)
        assert result["success"] is True
        assert result["context"]["fluid_transform"] == "fluid1"
        assert result["context"]["fluid_shape"] == "fluidShape1"

    def test_no_fluid_shape_created(self):
        """If Maya creates nothing, fluid_shape and fluid_transform are empty strings."""
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = []  # no fluidShape nodes
        result = _call(_fluid("create_fluid_container"), mock_cmds)
        assert result["success"] is True  # skill returns success even if shape is empty
        assert result["context"]["fluid_shape"] == ""
        assert result["context"]["fluid_transform"] == ""

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        result = _call(_fluid("create_fluid_container"), mock_cmds)
        assert result.get("prompt")

    def test_create3dfluid_called_with_correct_resolution(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        _call(_fluid("create_fluid_container"), mock_cmds, resolution=20)
        mock_cmds.create3dFluid.assert_called_once()
        call_kw = mock_cmds.create3dFluid.call_args[1]
        assert call_kw.get("resolutionW") == 20
        assert call_kw.get("resolutionH") == 20
        assert call_kw.get("resolutionD") == 20


class TestSetFluidAttribute:
    def test_missing_node(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = False
        result = _call(_fluid("set_fluid_attribute"), mock_cmds,
                       fluid_shape="badFluid", attribute="density", value=1.0)
        assert result["success"] is False

    def test_happy_path(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        result = _call(_fluid("set_fluid_attribute"), mock_cmds,
                       fluid_shape="fluidShape1", attribute="density", value=2.5)
        assert result["success"] is True
        assert result["context"]["value"] == 2.5
        assert result["context"]["attribute"] == "density"

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        result = _call(_fluid("set_fluid_attribute"), mock_cmds,
                       fluid_shape="fluidShape1", attribute="heat", value=0.5)
        assert result.get("prompt")


class TestListFluidContainers:
    def test_empty_scene(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = []
        result = _call(_fluid("list_fluid_containers"), mock_cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_single_container_with_resolution(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = [(10, 10, 10)]
        result = _call(_fluid("list_fluid_containers"), mock_cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["containers"][0]["transform"] == "fluid1"
        assert result["context"]["containers"][0]["resolution"] == [10, 10, 10]

    def test_container_without_resolution_attr(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = ["fluidShape1"]
        mock_cmds.listRelatives.return_value = ["fluid1"]
        mock_cmds.attributeQuery.return_value = False  # no resolution attr
        result = _call(_fluid("list_fluid_containers"), mock_cmds)
        assert result["context"]["containers"][0]["resolution"] is None

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.ls.return_value = []
        result = _call(_fluid("list_fluid_containers"), mock_cmds)
        assert result.get("prompt")


class TestDeleteFluidContainer:
    def test_missing_node(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = False
        result = _call(_fluid("delete_fluid_container"), mock_cmds, name="badFluid")
        assert result["success"] is False

    def test_happy_path(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        result = _call(_fluid("delete_fluid_container"), mock_cmds, name="fluid1")
        assert result["success"] is True
        assert result["context"]["deleted"] == "fluid1"
        mock_cmds.delete.assert_called_once_with("fluid1")

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        result = _call(_fluid("delete_fluid_container"), mock_cmds, name="fluid1")
        assert result.get("prompt")


# ===========================================================================
# Constraints
# ===========================================================================


class TestAddConstraint:
    def test_unknown_type(self):
        mock_cmds = MagicMock()
        result = _call(_constraint("add_constraint"), mock_cmds,
                       constraint_type="bad", source="obj1", target="obj2")
        assert result["success"] is False
        assert "Unknown" in result["message"]

    def test_missing_source(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.side_effect = [False, True]  # source missing
        result = _call(_constraint("add_constraint"), mock_cmds,
                       constraint_type="parent", source="badSrc", target="tgt")
        assert result["success"] is False

    def test_missing_target(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.side_effect = [True, False]  # target missing
        result = _call(_constraint("add_constraint"), mock_cmds,
                       constraint_type="parent", source="src", target="badTgt")
        assert result["success"] is False

    def test_happy_path_parent_constraint(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.parentConstraint.return_value = ["src_parentConstraint1"]
        result = _call(_constraint("add_constraint"), mock_cmds,
                       constraint_type="parent", source="src", target="tgt",
                       maintain_offset=True, weight=1.0)
        assert result["success"] is True
        assert result["context"]["constraint_node"] == "src_parentConstraint1"
        assert result["context"]["constraint_type"] == "parent"

    @pytest.mark.parametrize("ctype", ["point", "orient", "scale", "aim"])
    def test_all_supported_types(self, ctype):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        getattr(mock_cmds, {
            "point": "pointConstraint",
            "orient": "orientConstraint",
            "scale": "scaleConstraint",
            "aim": "aimConstraint",
        }[ctype]).return_value = ["constraint1"]
        result = _call(_constraint("add_constraint"), mock_cmds,
                       constraint_type=ctype, source="src", target="tgt")
        assert result["success"] is True

    def test_empty_constraint_result(self):
        """If Maya returns empty list, constraint_node should be empty string."""
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.pointConstraint.return_value = []
        result = _call(_constraint("add_constraint"), mock_cmds,
                       constraint_type="point", source="src", target="tgt")
        assert result["success"] is True
        assert result["context"]["constraint_node"] == ""

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.parentConstraint.return_value = ["c1"]
        result = _call(_constraint("add_constraint"), mock_cmds,
                       constraint_type="parent", source="s", target="t")
        assert result.get("prompt")


class TestCreateConstraintWeighted:
    def test_unknown_type(self):
        mock_cmds = MagicMock()
        result = _call(_constraint("create_constraint_weighted"), mock_cmds,
                       constraint_type="bad", sources=["s1"], target="tgt")
        assert result["success"] is False

    def test_no_sources(self):
        mock_cmds = MagicMock()
        result = _call(_constraint("create_constraint_weighted"), mock_cmds,
                       constraint_type="parent", sources=[], target="tgt")
        assert result["success"] is False
        assert "source" in result["message"].lower()

    def test_missing_source_node(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.side_effect = [False, True]
        result = _call(_constraint("create_constraint_weighted"), mock_cmds,
                       constraint_type="parent", sources=["bad"], target="tgt")
        assert result["success"] is False

    def test_single_source_happy_path(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.parentConstraint.return_value = ["src1_parentConstraint1"]
        result = _call(_constraint("create_constraint_weighted"), mock_cmds,
                       constraint_type="parent", sources=["src1"], target="tgt",
                       weights=[0.8])
        assert result["success"] is True
        assert result["context"]["constraint_node"] == "src1_parentConstraint1"
        assert len(result["context"]["source_weights"]) == 1
        assert result["context"]["source_weights"][0]["weight"] == 0.8

    def test_two_sources_with_weights(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.orientConstraint.return_value = ["c1"]
        result = _call(_constraint("create_constraint_weighted"), mock_cmds,
                       constraint_type="orient", sources=["s1", "s2"], target="tgt",
                       weights=[0.6, 0.4])
        assert result["success"] is True
        assert len(result["context"]["source_weights"]) == 2
        weights = {item["source"]: item["weight"] for item in result["context"]["source_weights"]}
        assert weights["s1"] == pytest.approx(0.6)
        assert weights["s2"] == pytest.approx(0.4)

    def test_weights_default_to_one(self):
        """When weights is None, defaults to 1.0 per source."""
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.pointConstraint.return_value = ["c1"]
        result = _call(_constraint("create_constraint_weighted"), mock_cmds,
                       constraint_type="point", sources=["s1", "s2"], target="tgt",
                       weights=None)
        assert result["success"] is True
        for item in result["context"]["source_weights"]:
            assert item["weight"] == pytest.approx(1.0)

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.scaleConstraint.return_value = ["c1"]
        result = _call(_constraint("create_constraint_weighted"), mock_cmds,
                       constraint_type="scale", sources=["s1"], target="tgt")
        assert result.get("prompt")


class TestListConstraints:
    def test_missing_node(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = False
        result = _call(_constraint("list_constraints"), mock_cmds, target="badObj")
        assert result["success"] is False

    def test_no_constraints(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = []
        mock_cmds.listConnections.return_value = []
        result = _call(_constraint("list_constraints"), mock_cmds, target="freeObj")
        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["constraints"] == []

    def test_two_constraint_types_found(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True

        def fake_listRelatives(target, type=None, **kw):
            if type == "parentConstraint":
                return ["pCon1"]
            return []

        def fake_listConnections(target_or_node, type=None, source=None, destination=None):
            if isinstance(target_or_node, str) and "pCon1" in target_or_node:
                return ["src1"]  # sources of pCon1
            if type == "pointConstraint":
                return ["ptCon1"]
            return []

        mock_cmds.listRelatives.side_effect = fake_listRelatives
        mock_cmds.listConnections.side_effect = fake_listConnections
        result = _call(_constraint("list_constraints"), mock_cmds, target="driven")
        assert result["success"] is True
        assert result["context"]["count"] >= 1

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = []
        mock_cmds.listConnections.return_value = []
        result = _call(_constraint("list_constraints"), mock_cmds, target="obj")
        assert result.get("prompt")


class TestRemoveConstraint:
    def test_missing_node(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = False
        result = _call(_constraint("remove_constraint"), mock_cmds, target="badObj")
        assert result["success"] is False

    def test_no_constraints_found(self):
        mock_cmds = MagicMock()
        # First objExists for validate_node_exists
        mock_cmds.objExists.side_effect = lambda n: n == "obj1"
        mock_cmds.listRelatives.return_value = []
        mock_cmds.listConnections.return_value = []
        result = _call(_constraint("remove_constraint"), mock_cmds, target="obj1")
        assert result["success"] is True
        assert result["context"]["removed"] == []

    def test_removes_all_constraint_types(self):
        mock_cmds = MagicMock()
        # First call is validate_node_exists; subsequent are objExists(node)
        call_count = [0]

        def fake_objExists(n):
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # validate_node_exists
            return True  # constraint node exists

        mock_cmds.objExists.side_effect = fake_objExists
        mock_cmds.listRelatives.side_effect = lambda *a, **kw: (
            ["obj1_parentConstraint1"] if kw.get("type") == "parentConstraint" else []
        )
        mock_cmds.listConnections.return_value = []
        result = _call(_constraint("remove_constraint"), mock_cmds, target="obj1")
        assert result["success"] is True
        assert "obj1_parentConstraint1" in result["context"]["removed"]

    def test_specific_type_only(self):
        """When constraint_type is specified, only that type is removed."""
        mock_cmds = MagicMock()
        call_count = [0]

        def fake_objExists(n):
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            return True

        mock_cmds.objExists.side_effect = fake_objExists
        mock_cmds.listRelatives.return_value = ["ptCon1"]
        mock_cmds.listConnections.return_value = []
        result = _call(_constraint("remove_constraint"), mock_cmds, target="obj1",
                       constraint_type="pointConstraint")
        assert result["success"] is True
        # Only pointConstraint should be checked (not all 8 types)
        assert mock_cmds.listRelatives.call_count == 1

    def test_prompt_present(self):
        mock_cmds = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = []
        mock_cmds.listConnections.return_value = []
        result = _call(_constraint("remove_constraint"), mock_cmds, target="obj")
        assert result.get("prompt")
