"""Round 20: tests for maya-scene-assembly, maya-instancer, maya-spline-ik skills."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

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
# maya-scene-assembly
# ===========================================================================


class TestCreateAssembly:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-scene-assembly", "create_assembly")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.assembly.return_value = "myAssembly"
        result = self.mod.run({"name": "myAssembly"})
        assert result.success is True
        assert "myAssembly" in result.message
        assert result.context["assembly_node"] == "myAssembly"

    def test_with_definition(self):
        self.mock_cmds.assembly.return_value = "asmRef1"
        result = self.mod.run({"name": "asmRef1", "definition": "/path/to/asset.ad"})
        assert result.success is True
        self.mock_cmds.setAttr.assert_called_once()

    def test_no_definition_skips_setattr(self):
        self.mock_cmds.assembly.return_value = "asmRef1"
        result = self.mod.run({"name": "asmRef1"})
        assert result.success is True
        self.mock_cmds.setAttr.assert_not_called()

    def test_empty_name_error(self):
        result = self.mod.run({"name": ""})
        assert result.success is False
        assert "required" in result.error.lower()

    def test_exception(self):
        self.mock_cmds.assembly.side_effect = RuntimeError("plug-in not loaded")
        result = self.mod.run({"name": "fail"})
        assert result.success is False
        assert "plug-in" in result.error.lower()

    def test_prompt_present(self):
        self.mock_cmds.assembly.return_value = "asm1"
        result = self.mod.run({"name": "asm1"})
        assert result.prompt


class TestListAssemblies:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-scene-assembly", "list_assemblies")

    def teardown_method(self):
        _cleanup_maya()

    def test_empty_scene(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_lists_nodes(self):
        self.mock_cmds.ls.return_value = ["asm1", "asm2"]
        self.mock_cmds.getAttr.return_value = "/path/asset.ad"
        self.mock_cmds.assembly.return_value = "Geometry"
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2
        assert result.context["assemblies"][0]["name"] == "asm1"

    def test_active_rep_exception_handled(self):
        self.mock_cmds.ls.return_value = ["asm1"]
        self.mock_cmds.getAttr.return_value = ""
        self.mock_cmds.assembly.side_effect = Exception("query failed")
        result = self.mod.run({})
        assert result.success is True
        assert result.context["assemblies"][0]["active_representation"] == ""

    def test_exception(self):
        self.mock_cmds.ls.side_effect = RuntimeError("scene error")
        result = self.mod.run({})
        assert result.success is False

    def test_prompt_present(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.prompt


class TestActivateAssemblyRepresentation:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-scene-assembly", "activate_assembly_representation")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "assemblyReference"
        result = self.mod.run({"assembly": "asm1", "representation": "GPU"})
        assert result.success is True
        assert "GPU" in result.message

    def test_missing_assembly_param(self):
        result = self.mod.run({"representation": "GPU"})
        assert result.success is False
        assert "required" in result.error.lower()

    def test_missing_representation_param(self):
        result = self.mod.run({"assembly": "asm1"})
        assert result.success is False

    def test_node_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"assembly": "missing", "representation": "GPU"})
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_wrong_node_type(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "transform"
        result = self.mod.run({"assembly": "badNode", "representation": "GPU"})
        assert result.success is False
        assert "assemblyreference" in result.error.lower()

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "assemblyReference"
        self.mock_cmds.assembly.side_effect = RuntimeError("cannot activate")
        result = self.mod.run({"assembly": "asm1", "representation": "GPU"})
        assert result.success is False


class TestListAssemblyRepresentations:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-scene-assembly", "list_assembly_representations")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True

        def _asm_side(node, **kwargs):
            if kwargs.get("listRepresentations"):
                return ["GPU", "Proxy", "Full"]
            if kwargs.get("activeRepresentation"):
                return "Proxy"
            return None

        self.mock_cmds.assembly.side_effect = _asm_side
        result = self.mod.run({"assembly": "asm1"})
        assert result.success is True
        assert result.context["count"] == 3
        assert result.context["active_representation"] == "Proxy"

    def test_missing_assembly_param(self):
        result = self.mod.run({})
        assert result.success is False

    def test_node_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"assembly": "missing"})
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.assembly.side_effect = RuntimeError("repr error")
        result = self.mod.run({"assembly": "asm1"})
        assert result.success is False

    def test_prompt_present(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.assembly.return_value = []
        result = self.mod.run({"assembly": "asm1"})
        assert result.prompt


class TestDeleteAssembly:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-scene-assembly", "delete_assembly")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "assemblyReference"
        result = self.mod.run({"assembly": "asm1"})
        assert result.success is True
        assert "asm1" in result.context["deleted_assembly"]
        self.mock_cmds.delete.assert_called_once_with("asm1")

    def test_empty_param(self):
        result = self.mod.run({})
        assert result.success is False

    def test_node_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"assembly": "ghost"})
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_wrong_type(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "transform"
        result = self.mod.run({"assembly": "badNode"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "assemblyReference"
        self.mock_cmds.delete.side_effect = RuntimeError("delete failed")
        result = self.mod.run({"assembly": "asm1"})
        assert result.success is False


# ===========================================================================
# maya-instancer
# ===========================================================================


class TestCreateInstancer:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-instancer", "create_instancer")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.particleInstancer.return_value = ["instancer1"]
        result = self.mod.run({
            "particle_system": "particle1",
            "instance_objects": ["pSphere1"],
        })
        assert result.success is True
        assert result.context["instancer"] == "instancer1"

    def test_with_name_and_cycle(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.particleInstancer.return_value = ["myInstancer"]
        result = self.mod.run({
            "particle_system": "nParticle1",
            "instance_objects": ["pCube1", "pSphere1"],
            "name": "myInstancer",
            "cycle": "Sequential",
        })
        assert result.success is True
        assert result.context["instancer"] == "myInstancer"

    def test_missing_particle_system(self):
        result = self.mod.run({"instance_objects": ["pSphere1"]})
        assert result.success is False
        assert "particle_system" in result.error.lower()

    def test_empty_instance_objects(self):
        result = self.mod.run({"particle_system": "p1", "instance_objects": []})
        assert result.success is False
        assert "instance_objects" in result.error.lower()

    def test_particle_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"particle_system": "ghost", "instance_objects": ["pSphere1"]})
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_unknown_cycle_mode_defaults(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.particleInstancer.return_value = ["inst1"]
        result = self.mod.run({
            "particle_system": "p1",
            "instance_objects": ["obj1"],
            "cycle": "Unknown",
        })
        assert result.success is True

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.particleInstancer.side_effect = RuntimeError("instancer error")
        result = self.mod.run({"particle_system": "p1", "instance_objects": ["obj1"]})
        assert result.success is False

    def test_prompt_present(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.particleInstancer.return_value = ["inst1"]
        result = self.mod.run({"particle_system": "p1", "instance_objects": ["obj1"]})
        assert result.prompt


class TestListInstancers:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-instancer", "list_instancers")

    def teardown_method(self):
        _cleanup_maya()

    def test_empty_scene(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_lists_nodes(self):
        self.mock_cmds.ls.return_value = ["instancer1", "instancer2"]
        self.mock_cmds.particleInstancer.return_value = ["pSphere1"]
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_query_failure_handled(self):
        self.mock_cmds.ls.return_value = ["instancer1"]
        self.mock_cmds.particleInstancer.side_effect = Exception("query error")
        result = self.mod.run({})
        assert result.success is True
        assert result.context["instancers"][0]["instance_objects"] == []

    def test_exception(self):
        self.mock_cmds.ls.side_effect = RuntimeError("scene error")
        result = self.mod.run({})
        assert result.success is False

    def test_prompt_present(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.prompt


class TestAddInstancerObject:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-instancer", "add_instancer_object")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "instancer"
        result = self.mod.run({
            "particle_system": "p1",
            "instancer": "instancer1",
            "object": "pCone1",
        })
        assert result.success is True
        assert result.context["added_object"] == "pCone1"

    def test_missing_params(self):
        result = self.mod.run({"particle_system": "p1"})
        assert result.success is False
        assert "required" in result.error.lower()

    def test_instancer_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({
            "particle_system": "p1",
            "instancer": "ghost",
            "object": "pSphere1",
        })
        assert result.success is False

    def test_wrong_node_type(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "transform"
        result = self.mod.run({
            "particle_system": "p1",
            "instancer": "badNode",
            "object": "pSphere1",
        })
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "instancer"
        self.mock_cmds.particleInstancer.side_effect = RuntimeError("add failed")
        result = self.mod.run({
            "particle_system": "p1",
            "instancer": "instancer1",
            "object": "pSphere1",
        })
        assert result.success is False


class TestSetInstancerAttribute:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-instancer", "set_instancer_attribute")

    def teardown_method(self):
        _cleanup_maya()

    def test_scalar_value(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"instancer": "inst1", "attribute": "cycle", "value": 1})
        assert result.success is True
        self.mock_cmds.setAttr.assert_called_once_with("inst1.cycle", 1)

    def test_string_value(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"instancer": "inst1", "attribute": "rotationOrder", "value": "xyz"})
        assert result.success is True
        self.mock_cmds.setAttr.assert_called_with("inst1.rotationOrder", "xyz", type="string")

    def test_list_value(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"instancer": "inst1", "attribute": "position", "value": [1.0, 2.0, 3.0]})
        assert result.success is True

    def test_missing_instancer(self):
        result = self.mod.run({"attribute": "cycle", "value": 1})
        assert result.success is False

    def test_missing_value(self):
        result = self.mod.run({"instancer": "inst1", "attribute": "cycle"})
        assert result.success is False

    def test_node_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"instancer": "ghost", "attribute": "cycle", "value": 0})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.setAttr.side_effect = RuntimeError("locked attr")
        result = self.mod.run({"instancer": "inst1", "attribute": "cycle", "value": 0})
        assert result.success is False


class TestDeleteInstancer:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-instancer", "delete_instancer")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "instancer"
        result = self.mod.run({"instancer": "instancer1"})
        assert result.success is True
        self.mock_cmds.delete.assert_called_once_with("instancer1")

    def test_empty_param(self):
        result = self.mod.run({})
        assert result.success is False

    def test_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"instancer": "ghost"})
        assert result.success is False

    def test_wrong_type(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "transform"
        result = self.mod.run({"instancer": "badNode"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "instancer"
        self.mock_cmds.delete.side_effect = RuntimeError("delete error")
        result = self.mod.run({"instancer": "inst1"})
        assert result.success is False


# ===========================================================================
# maya-spline-ik
# ===========================================================================


class TestCreateSplineIk:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-spline-ik", "create_spline_ik")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success_auto_curve(self):
        self.mock_cmds.ikHandle.return_value = ["spineIK", "spineEffector", "spineCurve"]
        result = self.mod.run({"start_joint": "joint1", "end_joint": "joint5"})
        assert result.success is True
        assert result.context["ik_handle"] == "spineIK"
        assert result.context["effector"] == "spineEffector"
        assert result.context["curve"] == "spineCurve"

    def test_with_existing_curve(self):
        self.mock_cmds.ikHandle.return_value = ["spineIK", "spineEffector"]
        result = self.mod.run({
            "start_joint": "joint1",
            "end_joint": "joint5",
            "curve": "spineCurve",
        })
        assert result.success is True

    def test_with_name(self):
        self.mock_cmds.ikHandle.return_value = ["spine_ikHandle", "spine_effector", "spineCurve"]
        result = self.mod.run({
            "start_joint": "joint1",
            "end_joint": "joint5",
            "name": "spine",
        })
        assert result.success is True
        assert result.context["ik_handle"] == "spine_ikHandle"

    def test_missing_start_joint(self):
        result = self.mod.run({"end_joint": "joint5"})
        assert result.success is False
        assert "required" in result.error.lower()

    def test_missing_end_joint(self):
        result = self.mod.run({"start_joint": "joint1"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.ikHandle.side_effect = RuntimeError("solver not found")
        result = self.mod.run({"start_joint": "joint1", "end_joint": "joint5"})
        assert result.success is False
        assert "solver" in result.error.lower()

    def test_prompt_present(self):
        self.mock_cmds.ikHandle.return_value = ["h", "e", "c"]
        result = self.mod.run({"start_joint": "j1", "end_joint": "j5"})
        assert result.prompt


class TestSetSplineIkStretch:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-spline-ik", "set_spline_ik_stretch")

    def teardown_method(self):
        _cleanup_maya()

    def test_enable_stretch_only(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"ik_handle": "spineIK", "stretch": True})
        assert result.success is True
        assert result.context["stretch"] is True
        assert result.context["squash"] is False

    def test_enable_both_stretch_and_squash(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"ik_handle": "spineIK", "stretch": True, "squash": True})
        assert result.success is True
        assert result.context["squash"] is True

    def test_disable_both(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"ik_handle": "spineIK", "stretch": False, "squash": False})
        assert result.success is True

    def test_missing_param(self):
        result = self.mod.run({})
        assert result.success is False

    def test_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"ik_handle": "ghost"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.setAttr.side_effect = RuntimeError("locked")
        result = self.mod.run({"ik_handle": "spineIK"})
        assert result.success is False

    def test_prompt_present(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"ik_handle": "spineIK"})
        assert result.prompt


class TestSetSplineIkTwist:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-spline-ik", "set_spline_ik_twist")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"ik_handle": "spineIK", "world_up_type": 1, "twist": 45.0})
        assert result.success is True
        assert result.context["world_up_type"] == 1
        assert result.context["twist"] == 45.0

    def test_defaults(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"ik_handle": "spineIK"})
        assert result.success is True
        assert result.context["world_up_type"] == 0
        assert result.context["twist"] == 0.0

    def test_missing_param(self):
        result = self.mod.run({})
        assert result.success is False

    def test_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"ik_handle": "ghost"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.setAttr.side_effect = RuntimeError("attr error")
        result = self.mod.run({"ik_handle": "spineIK"})
        assert result.success is False

    def test_prompt_present(self):
        self.mock_cmds.objExists.return_value = True
        result = self.mod.run({"ik_handle": "spineIK"})
        assert result.prompt


class TestListSplineIkHandles:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-spline-ik", "list_spline_ik_handles")

    def teardown_method(self):
        _cleanup_maya()

    def test_empty_scene(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_filters_spline_only(self):
        self.mock_cmds.ls.return_value = ["splineIK1", "rotateIK1"]

        def _ik_side(handle, **kwargs):
            if kwargs.get("solver"):
                return "ikSplineSolver" if "spline" in handle.lower() else "ikRPsolver"
            return None

        self.mock_cmds.ikHandle.side_effect = _ik_side
        self.mock_cmds.getAttr.return_value = True
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 1
        assert result.context["ik_handles"][0]["name"] == "splineIK1"

    def test_getattr_failure_handled(self):
        self.mock_cmds.ls.return_value = ["splineIK1"]
        self.mock_cmds.ikHandle.return_value = "ikSplineSolver"
        self.mock_cmds.getAttr.side_effect = Exception("attr missing")
        result = self.mod.run({})
        assert result.success is True
        assert result.context["ik_handles"][0]["stretch"] is False

    def test_exception(self):
        self.mock_cmds.ls.side_effect = RuntimeError("ls error")
        result = self.mod.run({})
        assert result.success is False

    def test_prompt_present(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.prompt


class TestDeleteSplineIk:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-spline-ik", "delete_spline_ik")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "ikHandle"
        result = self.mod.run({"ik_handle": "spineIK"})
        assert result.success is True
        assert result.context["deleted_ik_handle"] == "spineIK"
        assert result.context["deleted_curve"] is None

    def test_delete_with_curve(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "ikHandle"
        self.mock_cmds.ikHandle.return_value = ["spineCurve"]
        result = self.mod.run({"ik_handle": "spineIK", "delete_curve": True})
        assert result.success is True
        assert result.context["deleted_curve"] == "spineCurve"

    def test_empty_param(self):
        result = self.mod.run({})
        assert result.success is False

    def test_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"ik_handle": "ghost"})
        assert result.success is False

    def test_wrong_type(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "joint"
        result = self.mod.run({"ik_handle": "joint1"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "ikHandle"
        self.mock_cmds.delete.side_effect = RuntimeError("delete error")
        result = self.mod.run({"ik_handle": "spineIK"})
        assert result.success is False
