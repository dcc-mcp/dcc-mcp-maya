"""Round 26 – tests for validate_node_exists/batch_validate_nodes refactored skills.

Covers:
- api.py type annotation compatibility (Python 3.7+)
- maya-rigging: skin_cluster_bind, create_ik_handle, set_driven_key,
  set_ik_fk_blend, assign_deformer, set_joint_orient
- maya-dynamics: set_ncloth_attribute, set_nrigid_attribute
- maya-node-graph: connect_attr, disconnect_attr
- maya-mesh-ops: apply_subdivision, cleanup_mesh, triangulate
- maya-animation: set_keyframe, delete_keyframes
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

# Import third-party modules

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
_MOD_COUNTER = [0]


def _load_script(skill_dir: str, script_name: str) -> Any:
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r26_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides: Any):
    """Return (maya_mock, cmds_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    cmds_mock.objectType.return_value = "transform"
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


def _run_func(skill_dir: str, func_name: str, cmds_overrides: Optional[dict] = None, **kwargs: Any) -> dict:
    """Load a skill script, inject Maya mocks, and call its main function."""
    cmds_overrides = cmds_overrides or {}
    _, cmds_mock, modules = _make_maya_env(**cmds_overrides)
    with patch.dict(sys.modules, modules):
        mod = _load_script(skill_dir, func_name)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


# ---------------------------------------------------------------------------
# api.py type annotation smoke test
# ---------------------------------------------------------------------------


class TestApiTypeAnnotations:
    """Verify that api.py functions are importable and callable (Python 3.7 compat)."""

    def test_maya_success_returns_dict(self):
        from dcc_mcp_maya.api import maya_success

        r = maya_success("ok", prompt="next step", foo="bar")
        assert isinstance(r, dict)
        assert r["success"] is True

    def test_maya_error_default_empty_error(self):
        from dcc_mcp_maya.api import maya_error

        r = maya_error("fail")
        assert isinstance(r, dict)
        assert r["success"] is False

    def test_maya_error_with_possible_solutions(self):
        from dcc_mcp_maya.api import maya_error

        r = maya_error("fail", "detail", possible_solutions=["try this"])
        assert r["success"] is False

    def test_validate_node_exists_returns_none_when_exists(self):
        from dcc_mcp_maya.api import validate_node_exists

        cmds = MagicMock()
        cmds.objExists.return_value = True
        assert validate_node_exists(cmds, "node1") is None

    def test_validate_node_exists_returns_dict_when_missing(self):
        from dcc_mcp_maya.api import validate_node_exists

        cmds = MagicMock()
        cmds.objExists.return_value = False
        r = validate_node_exists(cmds, "missing")
        assert isinstance(r, dict)
        assert r["success"] is False

    def test_validate_node_type_returns_none_on_match(self):
        from dcc_mcp_maya.api import validate_node_type

        cmds = MagicMock()
        cmds.objectType.return_value = "joint"
        assert validate_node_type(cmds, "joint1", "joint") is None

    def test_validate_node_type_returns_dict_on_mismatch(self):
        from dcc_mcp_maya.api import validate_node_type

        cmds = MagicMock()
        cmds.objectType.return_value = "mesh"
        r = validate_node_type(cmds, "pSphere1", "joint")
        assert isinstance(r, dict)
        assert r["success"] is False
        assert r["message"].lower().startswith("wrong node type")

    def test_batch_validate_nodes_all_exist(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        cmds = MagicMock()
        cmds.objExists.return_value = True
        assert batch_validate_nodes(cmds, ["a", "b", "c"]) is None

    def test_batch_validate_nodes_first_missing(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        cmds = MagicMock()
        cmds.objExists.side_effect = lambda n: n != "missing"
        r = batch_validate_nodes(cmds, ["ok", "missing", "also_ok"])
        assert r is not None
        assert r["success"] is False

    def test_get_param_list_returns_list(self):
        from dcc_mcp_maya.api import get_param_list

        result = get_param_list({"items": ["a", "b"]}, "items")
        assert result == ["a", "b"]
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# maya-rigging: skin_cluster_bind
# ---------------------------------------------------------------------------


class TestSkinClusterBindRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.skinCluster.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "skin_cluster_bind")
            r = mod.skin_cluster_bind(joints=["joint1", "joint2"], mesh="pSphereShape1")
        assert r["success"] is True
        assert r["context"]["joint_count"] == 2

    def test_empty_joints(self):
        r = _run_func("maya-rigging", "skin_cluster_bind", joints=[], mesh="pSphereShape1")
        assert r["success"] is False
        assert "no joints" in r["message"].lower()

    def test_mesh_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "pSphereShape1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "skin_cluster_bind")
            r = mod.skin_cluster_bind(joints=["joint1"], mesh="pSphereShape1")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_joint_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "joint_missing"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "skin_cluster_bind")
            r = mod.skin_cluster_bind(joints=["joint_missing"], mesh="pMesh")
        assert r["success"] is False

    def test_uses_batch_validate_nodes_import(self):
        """Verify that the refactored script imports batch_validate_nodes."""
        script_path = _SKILLS_ROOT / "maya-rigging" / "scripts" / "skin_cluster_bind.py"
        content = script_path.read_text(encoding="utf-8")
        assert "batch_validate_nodes" in content


# ---------------------------------------------------------------------------
# maya-rigging: create_ik_handle
# ---------------------------------------------------------------------------


class TestCreateIkHandleRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ikHandle.return_value = ["ikHandle1", "effector1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "create_ik_handle")
            r = mod.create_ik_handle(start_joint="joint1", end_joint="joint3")
        assert r["success"] is True
        assert r["context"]["handle_name"] == "ikHandle1"

    def test_start_joint_missing(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "create_ik_handle")
            r = mod.create_ik_handle(start_joint="missing", end_joint="j3")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_invalid_solver(self):
        r = _run_func("maya-rigging", "create_ik_handle", start_joint="j1", end_joint="j3", solver="badSolver")
        assert r["success"] is False
        assert "solver" in r["message"].lower()

    def test_uses_batch_validate_nodes_import(self):
        script_path = _SKILLS_ROOT / "maya-rigging" / "scripts" / "create_ik_handle.py"
        content = script_path.read_text(encoding="utf-8")
        assert "batch_validate_nodes" in content


# ---------------------------------------------------------------------------
# maya-rigging: set_driven_key
# ---------------------------------------------------------------------------


class TestSetDrivenKeyRefactor:
    def test_happy_path(self):
        r = _run_func(
            "maya-rigging",
            "set_driven_key",
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.translateX"],
            driver_values=[0.0, 90.0],
            driven_values=[[0.0], [5.0]],
        )
        assert r["success"] is True
        assert r["context"]["key_count"] == 2

    def test_empty_driver_values(self):
        r = _run_func(
            "maya-rigging",
            "set_driven_key",
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.translateX"],
            driver_values=[],
            driven_values=[],
        )
        assert r["success"] is False
        assert "driver_values" in r["message"].lower()

    def test_driver_object_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "ctrl"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_driven_key")
            r = mod.set_driven_key(
                driver_attr="ctrl.rotateY",
                driven_attrs=["joint1.translateX"],
                driver_values=[0.0],
                driven_values=[[0.0]],
            )
        assert r["success"] is False

    def test_uses_validate_node_exists_import(self):
        script_path = _SKILLS_ROOT / "maya-rigging" / "scripts" / "set_driven_key.py"
        content = script_path.read_text(encoding="utf-8")
        assert "validate_node_exists" in content


# ---------------------------------------------------------------------------
# maya-rigging: assign_deformer
# ---------------------------------------------------------------------------


class TestAssignDeformerRefactor:
    def test_cluster_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.cluster.return_value = ["clusterNode1", "clusterHandle1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            r = mod.assign_deformer(object_name="pSphere1", deformer_type="cluster")
        assert r["success"] is True
        assert r["context"]["deformer_type"] == "cluster"

    def test_object_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            r = mod.assign_deformer(object_name="missing")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_unsupported_deformer(self):
        r = _run_func("maya-rigging", "assign_deformer", object_name="pSphere1", deformer_type="fakeDeformer")
        assert r["success"] is False
        assert "unsupported" in r["message"].lower()

    def test_uses_validate_node_exists_import(self):
        script_path = _SKILLS_ROOT / "maya-rigging" / "scripts" / "assign_deformer.py"
        content = script_path.read_text(encoding="utf-8")
        assert "validate_node_exists" in content


# ---------------------------------------------------------------------------
# maya-rigging: set_joint_orient
# ---------------------------------------------------------------------------


class TestSetJointOrientRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env(objectType=MagicMock(return_value="joint"))
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_joint_orient")
            r = mod.set_joint_orient(joint_name="joint1", orient=[10.0, 20.0, 30.0])
        assert r["success"] is True
        assert r["context"]["orient"] == [10.0, 20.0, 30.0]

    def test_joint_not_found_uses_validate(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_joint_orient")
            r = mod.set_joint_orient(joint_name="missing")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_wrong_type_uses_validate_node_type(self):
        _, cmds_mock, modules = _make_maya_env(objectType=MagicMock(return_value="mesh"))
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_joint_orient")
            r = mod.set_joint_orient(joint_name="pSphere1")
        assert r["success"] is False
        assert r["message"].lower().startswith("wrong node type")

    def test_default_orient_zeros(self):
        _, cmds_mock, modules = _make_maya_env(objectType=MagicMock(return_value="joint"))
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_joint_orient")
            r = mod.set_joint_orient(joint_name="joint1")
        assert r["success"] is True
        assert r["context"]["orient"] == [0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# maya-dynamics: set_ncloth_attribute
# ---------------------------------------------------------------------------


class TestSetNClothAttributeRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env(objectType=MagicMock(return_value="nCloth"))
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "set_ncloth_attribute")
            r = mod.set_ncloth_attribute(ncloth_node="nClothShape1", attribute="thickness", value=0.5)
        assert r["success"] is True

    def test_node_not_found_uses_validate(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "set_ncloth_attribute")
            r = mod.set_ncloth_attribute(ncloth_node="missing", attribute="thickness", value=0.5)
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_wrong_type_uses_validate_node_type(self):
        _, cmds_mock, modules = _make_maya_env(objectType=MagicMock(return_value="mesh"))
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "set_ncloth_attribute")
            r = mod.set_ncloth_attribute(ncloth_node="pSphere1", attribute="thickness", value=0.5)
        assert r["success"] is False
        assert r["message"].lower().startswith("wrong node type")

    def test_attribute_not_found(self):
        call_count = [0]

        def obj_exists_side(name):
            call_count[0] += 1
            return call_count[0] != 2  # node ok (1st), plug missing (2nd)

        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "nCloth"
        cmds_mock.objExists.side_effect = obj_exists_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "set_ncloth_attribute")
            r = mod.set_ncloth_attribute(ncloth_node="nClothShape1", attribute="badAttr", value=1.0)
        assert r["success"] is False
        assert "attribute" in r["message"].lower()


# ---------------------------------------------------------------------------
# maya-dynamics: set_nrigid_attribute
# ---------------------------------------------------------------------------


class TestSetNRigidAttributeRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env(objectType=MagicMock(return_value="nRigid"))
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "set_nrigid_attribute")
            r = mod.set_nrigid_attribute(nrigid_node="nRigidShape1", attribute="bounce", value=0.3)
        assert r["success"] is True

    def test_node_not_found_uses_validate(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "set_nrigid_attribute")
            r = mod.set_nrigid_attribute(nrigid_node="missing", attribute="bounce", value=0.3)
        assert r["success"] is False

    def test_wrong_type_uses_validate_node_type(self):
        _, cmds_mock, modules = _make_maya_env(objectType=MagicMock(return_value="mesh"))
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "set_nrigid_attribute")
            r = mod.set_nrigid_attribute(nrigid_node="pSphere1", attribute="bounce", value=0.3)
        assert r["success"] is False
        assert r["message"].lower().startswith("wrong node type")

    def test_empty_nrigid_node_fails(self):
        r = _run_func("maya-dynamics", "set_nrigid_attribute", nrigid_node="", attribute="bounce", value=0.3)
        assert r["success"] is False


# ---------------------------------------------------------------------------
# maya-node-graph: connect_attr
# ---------------------------------------------------------------------------


class TestConnectAttrRefactor:
    def test_happy_path(self):
        r = _run_func("maya-node-graph", "connect_attr", source_attr="pSphere1.tx", dest_attr="locator1.tx")
        assert r["success"] is True
        assert r["context"]["source_attr"] == "pSphere1.tx"

    def test_source_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "pSphere1.tx"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "connect_attr")
            r = mod.connect_attr(source_attr="pSphere1.tx", dest_attr="locator1.tx")
        assert r["success"] is False

    def test_dest_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "locator1.tx"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "connect_attr")
            r = mod.connect_attr(source_attr="pSphere1.tx", dest_attr="locator1.tx")
        assert r["success"] is False

    def test_uses_batch_validate_nodes(self):
        script_path = _SKILLS_ROOT / "maya-node-graph" / "scripts" / "connect_attr.py"
        content = script_path.read_text(encoding="utf-8")
        assert "batch_validate_nodes" in content


# ---------------------------------------------------------------------------
# maya-node-graph: disconnect_attr
# ---------------------------------------------------------------------------


class TestDisconnectAttrRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.isConnected.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "disconnect_attr")
            r = mod.disconnect_attr(source_attr="pSphere1.tx", dest_attr="locator1.tx")
        assert r["success"] is True

    def test_source_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "pSphere1.tx"
        cmds_mock.isConnected.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "disconnect_attr")
            r = mod.disconnect_attr(source_attr="pSphere1.tx", dest_attr="locator1.tx")
        assert r["success"] is False

    def test_not_connected_error(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.isConnected.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "disconnect_attr")
            r = mod.disconnect_attr(source_attr="pSphere1.tx", dest_attr="locator1.tx")
        assert r["success"] is False
        assert "not connected" in r["message"].lower()


# ---------------------------------------------------------------------------
# maya-mesh-ops: apply_subdivision
# ---------------------------------------------------------------------------


class TestApplySubdivisionRefactor:
    def test_preview_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listRelatives.return_value = ["pSphereShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            r = mod.apply_subdivision(object_name="pSphere1", level=2, method="preview")
        assert r["success"] is True

    def test_object_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            r = mod.apply_subdivision(object_name="missing")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_invalid_method(self):
        r = _run_func("maya-mesh-ops", "apply_subdivision", object_name="pSphere1", method="bad")
        assert r["success"] is False

    def test_uses_validate_node_exists(self):
        script_path = _SKILLS_ROOT / "maya-mesh-ops" / "scripts" / "apply_subdivision.py"
        content = script_path.read_text(encoding="utf-8")
        assert "validate_node_exists" in content


# ---------------------------------------------------------------------------
# maya-mesh-ops: cleanup_mesh
# ---------------------------------------------------------------------------


class TestCleanupMeshRefactor:
    def test_happy_path(self):
        r = _run_func("maya-mesh-ops", "cleanup_mesh", object_name="pSphere1")
        assert r["success"] is True

    def test_object_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "cleanup_mesh")
            r = mod.cleanup_mesh(object_name="missing")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()


# ---------------------------------------------------------------------------
# maya-mesh-ops: triangulate
# ---------------------------------------------------------------------------


class TestTriangulateRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.polyEvaluate.return_value = 100
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "triangulate")
            r = mod.triangulate(object_name="pSphere1")
        assert r["success"] is True

    def test_object_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "triangulate")
            r = mod.triangulate(object_name="missing")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()


# ---------------------------------------------------------------------------
# maya-animation: set_keyframe
# ---------------------------------------------------------------------------


class TestSetKeyframeRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.setKeyframe.return_value = 1
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-animation", "set_keyframe")
            r = mod.set_keyframe(object_name="pSphere1")
        assert r["success"] is True
        assert r["context"]["keyframe_count"] == 1

    def test_object_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-animation", "set_keyframe")
            r = mod.set_keyframe(object_name="missing")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_with_attribute_and_time(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.setKeyframe.return_value = 1
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-animation", "set_keyframe")
            r = mod.set_keyframe(object_name="pSphere1", attribute="translateX", time=10.0, value=5.0)
        assert r["success"] is True

    def test_uses_validate_node_exists(self):
        script_path = _SKILLS_ROOT / "maya-animation" / "scripts" / "set_keyframe.py"
        content = script_path.read_text(encoding="utf-8")
        assert "validate_node_exists" in content


# ---------------------------------------------------------------------------
# maya-animation: delete_keyframes
# ---------------------------------------------------------------------------


class TestDeleteKeyframesRefactor:
    def test_happy_path(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.cutKey.return_value = 3
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-animation", "delete_keyframes")
            r = mod.delete_keyframes(object_name="pSphere1")
        assert r["success"] is True
        assert r["context"]["deleted_count"] == 3

    def test_object_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-animation", "delete_keyframes")
            r = mod.delete_keyframes(object_name="missing")
        assert r["success"] is False
        assert "node not found" in r["message"].lower()

    def test_with_frame_range(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.cutKey.return_value = 5
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-animation", "delete_keyframes")
            r = mod.delete_keyframes(object_name="pSphere1", start_frame=1.0, end_frame=24.0)
        assert r["success"] is True
        assert r["context"]["start_frame"] == 1.0
