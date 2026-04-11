"""Round 6 skill tests: maya-attributes / maya-dynamics / maya-rigging (remaining).

All Maya API calls are mocked – no real Maya installation needed.
Scripts are loaded via importlib to handle hyphenated directory names.
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
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r6_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
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


def _run_func(skill_dir, func_name, cmds_overrides=None, **kwargs):
    """Load a skill script, inject Maya mocks, and call its main function."""
    cmds_overrides = cmds_overrides or {}
    _, cmds_mock, modules = _make_maya_env(**cmds_overrides)
    with patch.dict(sys.modules, modules):
        mod = _load_script(skill_dir, func_name)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


# ===========================================================================
# maya-attributes – add_attribute
# ===========================================================================


class TestAddAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-attributes", "add_attribute", cmds_overrides, **kwargs)

    def test_success_float(self):
        result = self._run(node_name="pSphere1", attribute="myFloat", attr_type="float")
        assert result["success"] is True
        assert result["context"]["attribute"] == "myFloat"
        assert result["context"]["attr_type"] == "float"

    def test_success_string_type(self):
        result = self._run(node_name="pSphere1", attribute="myStr", attr_type="string")
        assert result["success"] is True
        assert result["context"]["attr_type"] == "string"

    def test_node_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, node_name="missing", attribute="x")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_invalid_attr_type(self):
        result = self._run(node_name="pSphere1", attribute="x", attr_type="bogusType")
        assert result["success"] is False
        assert "invalid attribute type" in result["message"].lower()

    def test_with_min_max(self):
        result = self._run(node_name="pSphere1", attribute="clamped", attr_type="float", min_value=0.0, max_value=1.0)
        assert result["success"] is True

    def test_with_default_value(self):
        result = self._run(node_name="pSphere1", attribute="defVal", attr_type="double", default_value=3.14)
        assert result["success"] is True

    def test_keyable_false(self):
        result = self._run(node_name="pSphere1", attribute="hidden", attr_type="bool", keyable=False)
        assert result["success"] is True
        assert result["context"]["keyable"] is False


# ===========================================================================
# maya-attributes – set_attribute
# ===========================================================================


class TestSetAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-attributes", "set_attribute", cmds_overrides, **kwargs)

    def test_success_scalar(self):
        result = self._run(node_name="pSphere1", attribute="translateX", value=5.0)
        assert result["success"] is True
        assert result["context"]["value"] == 5.0

    def test_success_string_value(self):
        result = self._run(node_name="pSphere1", attribute="notes", value="hello")
        assert result["success"] is True

    def test_success_list_value(self):
        result = self._run(node_name="pSphere1", attribute="translate", value=[1, 2, 3])
        assert result["success"] is True

    def test_node_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, node_name="ghost", attribute="tx", value=1.0)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_attribute_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            # first call: node exists; second call: attr does not
            return call_count[0] == 1

        result = self._run({"objExists": obj_exists}, node_name="pSphere1", attribute="noSuchAttr", value=1.0)
        assert result["success"] is False

    def test_exception_propagates(self):
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = True
        cmds_mock.setAttr.side_effect = RuntimeError("locked")
        result = self._run(
            {"objExists": cmds_mock.objExists, "setAttr": cmds_mock.setAttr},
            node_name="pSphere1",
            attribute="tx",
            value=0.0,
        )
        assert result["success"] is False


# ===========================================================================
# maya-attributes – get_attribute
# ===========================================================================


class TestGetAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-attributes", "get_attribute", cmds_overrides, **kwargs)

    def test_success_scalar(self):
        result = self._run({"getAttr": MagicMock(return_value=3.0)}, node_name="pSphere1", attribute="translateX")
        assert result["success"] is True
        assert result["context"]["value"] == 3.0

    def test_success_compound_flattened(self):
        # cmds.getAttr returns [(x, y, z)] for compound attrs
        result = self._run(
            {"getAttr": MagicMock(return_value=[(1.0, 2.0, 3.0)])}, node_name="pSphere1", attribute="translate"
        )
        assert result["success"] is True
        assert result["context"]["value"] == [1.0, 2.0, 3.0]

    def test_node_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, node_name="missing", attribute="tx")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_attribute_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return call_count[0] == 1

        result = self._run({"objExists": obj_exists}, node_name="pSphere1", attribute="noSuchAttr")
        assert result["success"] is False

    def test_exception_propagates(self):
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = True
        cmds_mock.getAttr.side_effect = RuntimeError("no attr")
        result = self._run(
            {"objExists": cmds_mock.objExists, "getAttr": cmds_mock.getAttr}, node_name="pSphere1", attribute="tx"
        )
        assert result["success"] is False


# ===========================================================================
# maya-attributes – list_attributes
# ===========================================================================


class TestListAttributes:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-attributes", "list_attributes", cmds_overrides, **kwargs)

    def test_success_all(self):
        result = self._run({"listAttr": MagicMock(return_value=["tx", "ty", "tz"])}, node_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 3
        assert "tx" in result["context"]["attributes"]

    def test_success_empty(self):
        result = self._run({"listAttr": MagicMock(return_value=[])}, node_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_success_user_defined_only(self):
        result = self._run(
            {"listAttr": MagicMock(return_value=["myFloat"])}, node_name="pSphere1", user_defined_only=True
        )
        assert result["success"] is True
        assert result["context"]["attributes"] == ["myFloat"]

    def test_success_keyable_only(self):
        result = self._run({"listAttr": MagicMock(return_value=["tx", "ty"])}, node_name="pSphere1", keyable_only=True)
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_node_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, node_name="ghost")
        assert result["success"] is False
        assert "not found" in result["message"].lower()


# ===========================================================================
# maya-attributes – delete_attribute
# ===========================================================================


class TestDeleteAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-attributes", "delete_attribute", cmds_overrides, **kwargs)

    def test_success(self):
        result = self._run({"attributeQuery": MagicMock(return_value=True)}, node_name="pSphere1", attribute="myFloat")
        assert result["success"] is True
        assert result["context"]["attribute"] == "myFloat"

    def test_node_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, node_name="missing", attribute="myFloat")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_attribute_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return call_count[0] == 1

        result = self._run({"objExists": obj_exists}, node_name="pSphere1", attribute="noSuchAttr")
        assert result["success"] is False

    def test_builtin_attribute_rejected(self):
        result = self._run(
            {"attributeQuery": MagicMock(return_value=False)}, node_name="pSphere1", attribute="translateX"
        )
        assert result["success"] is False
        assert "built-in" in result["message"].lower()

    def test_exception_propagates(self):
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = True
        cmds_mock.attributeQuery.return_value = True
        cmds_mock.deleteAttr.side_effect = RuntimeError("cannot delete")
        result = self._run(
            {
                "objExists": cmds_mock.objExists,
                "attributeQuery": cmds_mock.attributeQuery,
                "deleteAttr": cmds_mock.deleteAttr,
            },
            node_name="pSphere1",
            attribute="myFloat",
        )
        assert result["success"] is False


# ===========================================================================
# maya-dynamics – create_nucleus
# ===========================================================================


class TestCreateNucleus:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-dynamics", "create_nucleus", cmds_overrides, **kwargs)

    def test_success_default(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createNode.return_value = "nucleus1"
        cmds_mock.ls.return_value = ["time1"]
        cmds_mock.isConnected.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nucleus")
            result = mod.create_nucleus()
        assert result["success"] is True
        assert result["context"]["nucleus_node"] == "nucleus1"
        assert result["context"]["gravity"] == -9.8

    def test_success_named(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createNode.return_value = "myNucleus"
        cmds_mock.ls.return_value = ["time1"]
        cmds_mock.isConnected.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nucleus")
            result = mod.create_nucleus(name="myNucleus", gravity=-5.0, wind_speed=2.0)
        assert result["success"] is True
        assert result["context"]["wind_speed"] == 2.0

    def test_custom_wind_direction(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createNode.return_value = "nucleus1"
        cmds_mock.ls.return_value = ["time1"]
        cmds_mock.isConnected.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nucleus")
            result = mod.create_nucleus(wind_direction=[1.0, 0.0, 0.0])
        assert result["success"] is True
        assert result["context"]["wind_direction"] == [1.0, 0.0, 0.0]

    def test_already_connected(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createNode.return_value = "nucleus1"
        cmds_mock.ls.return_value = ["time1"]
        cmds_mock.isConnected.return_value = True  # already connected
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nucleus")
            result = mod.create_nucleus()
        assert result["success"] is True

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createNode.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nucleus")
            result = mod.create_nucleus()
        assert result["success"] is False


# ===========================================================================
# maya-dynamics – create_ncloth
# ===========================================================================


class TestCreateNCloth:
    def _run_direct(self, cmds_mock_cfg, **kwargs):
        _, cmds_mock, modules = _make_maya_env()
        for k, v in cmds_mock_cfg.items():
            setattr(cmds_mock, k, v)
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_ncloth")
            return mod.create_ncloth(**kwargs)

    def test_success_named(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.nCloth.return_value = ["nClothShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_ncloth")
            result = mod.create_ncloth(mesh="pPlane1")
        assert result["success"] is True
        assert result["context"]["mesh"] == "pPlane1"

    def test_mesh_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_ncloth")
            result = mod.create_ncloth(mesh="missing")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_invalid_mesh_type(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "camera"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_ncloth")
            result = mod.create_ncloth(mesh="camera1")
        assert result["success"] is False
        assert "invalid mesh type" in result["message"].lower()

    def test_nucleus_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            # first: mesh exists; second: nucleus does not
            return call_count[0] == 1

        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists = obj_exists
        cmds_mock.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_ncloth")
            result = mod.create_ncloth(mesh="pPlane1", nucleus="missingNucleus")
        assert result["success"] is False
        assert "nucleus" in result["message"].lower()

    def test_with_specific_nucleus(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.nCloth.return_value = ["nClothShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_ncloth")
            result = mod.create_ncloth(mesh="pPlane1", nucleus="nucleus1")
        assert result["success"] is True
        assert result["context"]["nucleus"] == "nucleus1"


# ===========================================================================
# maya-dynamics – create_nrigid
# ===========================================================================


class TestCreateNRigid:
    def test_success(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.nRigid.return_value = ["nRigidShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nrigid")
            result = mod.create_nrigid(mesh="pCube1")
        assert result["success"] is True
        assert result["context"]["mesh"] == "pCube1"
        assert result["context"]["nrigid_node"] == "nRigidShape1"

    def test_mesh_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nrigid")
            result = mod.create_nrigid(mesh="missing")
        assert result["success"] is False

    def test_invalid_type(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "light"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nrigid")
            result = mod.create_nrigid(mesh="spotLight1")
        assert result["success"] is False

    def test_with_nucleus(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.nRigid.return_value = ["nRigidShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nrigid")
            result = mod.create_nrigid(mesh="pCube1", nucleus="nucleus1")
        assert result["success"] is True
        assert result["context"]["nucleus"] == "nucleus1"

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.nRigid.side_effect = RuntimeError("boom")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_nrigid")
            result = mod.create_nrigid(mesh="pCube1")
        assert result["success"] is False


# ===========================================================================
# maya-dynamics – create_dynamic_field
# ===========================================================================


class TestCreateDynamicField:
    def test_success_gravity(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.gravity.return_value = ["gravityField1"]
        cmds_mock.objExists.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_dynamic_field")
            result = mod.create_dynamic_field(field_type="gravity")
        assert result["success"] is True
        assert result["context"]["field_type"] == "gravity"

    def test_success_with_name(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.turbulence.return_value = ["myTurb"]
        cmds_mock.objExists.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_dynamic_field")
            result = mod.create_dynamic_field(field_type="turbulence", name="myTurb")
        assert result["success"] is True
        assert result["context"]["field_node"] == "myTurb"

    def test_invalid_field_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_dynamic_field")
            result = mod.create_dynamic_field(field_type="bogus")
        assert result["success"] is False
        assert "invalid field type" in result["message"].lower()

    def test_with_connected_objects(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.gravity.return_value = ["gravityField1"]
        cmds_mock.objExists.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_dynamic_field")
            result = mod.create_dynamic_field(field_type="gravity", objects=["nParticle1"])
        assert result["success"] is True
        assert "nParticle1" in result["context"]["connected_objects"]

    def test_missing_connected_objects(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            # field exists; particle object missing
            if "nParticle" in str(name):
                return False
            return True

        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.gravity.return_value = ["gravityField1"]
        cmds_mock.objExists = obj_exists
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "create_dynamic_field")
            result = mod.create_dynamic_field(field_type="gravity", objects=["nParticle_missing"])
        assert result["success"] is False


# ===========================================================================
# maya-dynamics – connect_field_to_objects
# ===========================================================================


class TestConnectFieldToObjects:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-dynamics", "connect_field_to_objects", cmds_overrides, **kwargs)

    def test_success(self):
        result = self._run(field_node="gravityField1", objects=["nParticle1"])
        assert result["success"] is True
        assert result["context"]["field_node"] == "gravityField1"
        assert "nParticle1" in result["context"]["connected_objects"]

    def test_empty_objects(self):
        result = self._run(field_node="gravityField1", objects=[])
        assert result["success"] is False
        assert "no objects" in result["message"].lower()

    def test_field_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, field_node="missing", objects=["nParticle1"])
        assert result["success"] is False

    def test_object_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return call_count[0] == 1  # field exists; particle missing

        result = self._run({"objExists": obj_exists}, field_node="gravityField1", objects=["ghost"])
        assert result["success"] is False

    def test_multiple_objects(self):
        result = self._run(field_node="turbField1", objects=["nParticle1", "nParticle2", "nCloth1"])
        assert result["success"] is True
        assert len(result["context"]["connected_objects"]) == 3


# ===========================================================================
# maya-dynamics – set_ncloth_attribute
# ===========================================================================


class TestSetNClothAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-dynamics", "set_ncloth_attribute", cmds_overrides, **kwargs)

    def test_success_scalar(self):
        result = self._run(
            {"objectType": MagicMock(return_value="nCloth")},
            ncloth_node="nClothShape1",
            attribute="thickness",
            value=0.1,
        )
        assert result["success"] is True
        assert result["context"]["value"] == 0.1

    def test_success_vector(self):
        result = self._run(
            {"objectType": MagicMock(return_value="nCloth")},
            ncloth_node="nClothShape1",
            attribute="inputForce",
            value=[0.0, 1.0, 0.0],
        )
        assert result["success"] is True

    def test_node_not_found(self):
        result = self._run(
            {"objExists": MagicMock(return_value=False)}, ncloth_node="missing", attribute="thickness", value=0.1
        )
        assert result["success"] is False

    def test_wrong_node_type(self):
        result = self._run(
            {"objectType": MagicMock(return_value="mesh")}, ncloth_node="pPlane1Shape", attribute="thickness", value=0.1
        )
        assert result["success"] is False
        assert result["message"].lower().startswith("wrong node type")

    def test_attribute_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            # node exists (1st call), attr path does not (2nd call)
            return call_count[0] == 1

        result = self._run(
            {"objExists": obj_exists, "objectType": MagicMock(return_value="nCloth")},
            ncloth_node="nClothShape1",
            attribute="noSuchAttr",
            value=1.0,
        )
        assert result["success"] is False


# ===========================================================================
# maya-dynamics – set_nrigid_attribute
# ===========================================================================


class TestSetNRigidAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-dynamics", "set_nrigid_attribute", cmds_overrides, **kwargs)

    def test_success_scalar(self):
        result = self._run(
            {"objectType": MagicMock(return_value="nRigid")}, nrigid_node="nRigidShape1", attribute="bounce", value=0.5
        )
        assert result["success"] is True
        assert result["context"]["value"] == 0.5

    def test_success_list_value(self):
        result = self._run(
            {"objectType": MagicMock(return_value="nRigid")},
            nrigid_node="nRigidShape1",
            attribute="someVec",
            value=[1.0, 2.0, 3.0],
        )
        assert result["success"] is True

    def test_missing_required_args(self):
        result = self._run(nrigid_node="", attribute="bounce", value=0.5)
        assert result["success"] is False

    def test_node_not_found(self):
        result = self._run(
            {"objExists": MagicMock(return_value=False)}, nrigid_node="missing", attribute="bounce", value=0.5
        )
        assert result["success"] is False

    def test_wrong_node_type(self):
        result = self._run(
            {"objectType": MagicMock(return_value="mesh")}, nrigid_node="pCubeShape1", attribute="bounce", value=0.5
        )
        assert result["success"] is False
        assert result["message"].lower().startswith("wrong node type")


# ===========================================================================
# maya-dynamics – set_nucleus_attribute
# ===========================================================================


class TestSetNucleusAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-dynamics", "set_nucleus_attribute", cmds_overrides, **kwargs)

    def test_success_scalar(self):
        result = self._run(
            {"objectType": MagicMock(return_value="nucleus")}, nucleus="nucleus1", attribute="gravity", value=-9.8
        )
        assert result["success"] is True

    def test_success_vector(self):
        result = self._run(
            {"objectType": MagicMock(return_value="nucleus")},
            nucleus="nucleus1",
            attribute="windDirection",
            value=[1.0, 0.0, 0.0],
        )
        assert result["success"] is True

    def test_node_not_found(self):
        result = self._run(
            {"objExists": MagicMock(return_value=False)}, nucleus="missing", attribute="gravity", value=0.0
        )
        assert result["success"] is False

    def test_wrong_node_type(self):
        result = self._run(
            {"objectType": MagicMock(return_value="transform")}, nucleus="pSphere1", attribute="gravity", value=0.0
        )
        assert result["success"] is False
        assert "not a nucleus" in result["message"].lower()

    def test_attribute_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return call_count[0] == 1

        result = self._run(
            {"objExists": obj_exists, "objectType": MagicMock(return_value="nucleus")},
            nucleus="nucleus1",
            attribute="noSuchAttr",
            value=0.0,
        )
        assert result["success"] is False


# ===========================================================================
# maya-dynamics – list_ncloth_nodes
# ===========================================================================


class TestListNClothNodes:
    def test_success_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "list_ncloth_nodes")
            result = mod.list_ncloth_nodes()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_success_with_nodes(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["nClothShape1"]
        cmds_mock.listRelatives.return_value = ["pPlane1"]
        cmds_mock.listConnections.return_value = ["nucleus1"]
        cmds_mock.objectType.return_value = "nucleus"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "list_ncloth_nodes")
            result = mod.list_ncloth_nodes()
        assert result["success"] is True
        assert result["context"]["count"] == 1
        node = result["context"]["nodes"][0]
        assert node["name"] == "nClothShape1"
        assert node["transform"] == "pPlane1"
        assert node["nucleus"] == "nucleus1"

    def test_no_nucleus_connected(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["nClothShape1"]
        cmds_mock.listRelatives.return_value = []
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "list_ncloth_nodes")
            result = mod.list_ncloth_nodes()
        assert result["success"] is True
        assert result["context"]["nodes"][0]["nucleus"] is None

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "list_ncloth_nodes")
            result = mod.list_ncloth_nodes()
        assert result["success"] is False


# ===========================================================================
# maya-dynamics – list_nrigid_nodes
# ===========================================================================


class TestListNRigidNodes:
    def test_success_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "list_nrigid_nodes")
            result = mod.list_nrigid_nodes()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_success_with_nodes(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["nRigidShape1"]
        cmds_mock.listRelatives.return_value = ["pCube1"]
        cmds_mock.listConnections.return_value = ["nucleus1"]
        cmds_mock.objectType.return_value = "nucleus"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "list_nrigid_nodes")
            result = mod.list_nrigid_nodes()
        assert result["success"] is True
        assert result["context"]["count"] == 1
        node = result["context"]["nodes"][0]
        assert node["transform"] == "pCube1"
        assert node["nucleus"] == "nucleus1"

    def test_no_parent(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["nRigidShape1"]
        cmds_mock.listRelatives.return_value = None
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-dynamics", "list_nrigid_nodes")
            result = mod.list_nrigid_nodes()
        assert result["success"] is True
        assert result["context"]["nodes"][0]["transform"] is None


# ===========================================================================
# maya-rigging – set_ik_fk_blend
# ===========================================================================


class TestSetIkFkBlend:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-rigging", "set_ik_fk_blend", cmds_overrides, **kwargs)

    def test_success_full_ik(self):
        result = self._run({"objectType": MagicMock(return_value="ikHandle")}, ik_handle="ikHandle1", blend=1.0)
        assert result["success"] is True
        assert result["context"]["blend"] == 1.0

    def test_success_full_fk(self):
        result = self._run({"objectType": MagicMock(return_value="ikHandle")}, ik_handle="ikHandle1", blend=0.0)
        assert result["success"] is True

    def test_success_mid_blend(self):
        result = self._run({"objectType": MagicMock(return_value="transform")}, ik_handle="ikHandle1", blend=0.5)
        assert result["success"] is True

    def test_blend_out_of_range_high(self):
        result = self._run(ik_handle="ikHandle1", blend=1.5)
        assert result["success"] is False
        assert "range" in result["message"].lower()

    def test_blend_out_of_range_low(self):
        result = self._run(ik_handle="ikHandle1", blend=-0.1)
        assert result["success"] is False

    def test_ik_handle_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, ik_handle="missing", blend=1.0)
        assert result["success"] is False

    def test_wrong_node_type(self):
        result = self._run({"objectType": MagicMock(return_value="joint")}, ik_handle="joint1", blend=1.0)
        assert result["success"] is False
        assert "not an ik handle" in result["message"].lower()

    def test_attribute_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return call_count[0] == 1

        result = self._run(
            {"objExists": obj_exists, "objectType": MagicMock(return_value="ikHandle")},
            ik_handle="ikHandle1",
            blend=1.0,
        )
        assert result["success"] is False


# ===========================================================================
# maya-rigging – set_joint_limit
# ===========================================================================


class TestSetJointLimit:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-rigging", "set_joint_limit", cmds_overrides, **kwargs)

    def test_success_x_axis(self):
        result = self._run(
            {"objectType": MagicMock(return_value="joint"), "getAttr": MagicMock(return_value=-45.0)},
            joint_name="joint1",
            axis="x",
            min_angle=-90.0,
            max_angle=90.0,
        )
        assert result["success"] is True
        assert result["context"]["axis"] == "x"
        assert result["context"]["enable"] is True

    def test_success_disable_limit(self):
        result = self._run(
            {"objectType": MagicMock(return_value="joint"), "getAttr": MagicMock(return_value=0.0)},
            joint_name="joint1",
            axis="y",
            enable=False,
        )
        assert result["success"] is True
        assert result["context"]["enable"] is False

    def test_joint_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, joint_name="missing", axis="x")
        assert result["success"] is False

    def test_wrong_node_type(self):
        result = self._run({"objectType": MagicMock(return_value="transform")}, joint_name="pSphere1", axis="x")
        assert result["success"] is False
        assert "not a joint" in result["message"].lower()

    def test_invalid_axis(self):
        result = self._run({"objectType": MagicMock(return_value="joint")}, joint_name="joint1", axis="w")
        assert result["success"] is False
        assert "invalid axis" in result["message"].lower()

    def test_only_min_angle(self):
        result = self._run(
            {"objectType": MagicMock(return_value="joint"), "getAttr": MagicMock(return_value=-30.0)},
            joint_name="joint1",
            axis="z",
            min_angle=-30.0,
        )
        assert result["success"] is True

    def test_exception_propagates(self):
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "joint"
        cmds_mock.setAttr.side_effect = RuntimeError("boom")
        result = self._run(
            {"objExists": cmds_mock.objExists, "objectType": cmds_mock.objectType, "setAttr": cmds_mock.setAttr},
            joint_name="joint1",
            axis="x",
        )
        assert result["success"] is False


# ===========================================================================
# maya-rigging – set_joint_orient
# ===========================================================================


class TestSetJointOrient:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-rigging", "set_joint_orient", cmds_overrides, **kwargs)

    def test_success_default_zero(self):
        result = self._run({"objectType": MagicMock(return_value="joint")}, joint_name="joint1")
        assert result["success"] is True
        assert result["context"]["orient"] == [0.0, 0.0, 0.0]

    def test_success_custom_orient(self):
        result = self._run(
            {"objectType": MagicMock(return_value="joint")}, joint_name="joint1", orient=[45.0, 0.0, 0.0]
        )
        assert result["success"] is True
        assert result["context"]["orient"] == [45.0, 0.0, 0.0]

    def test_success_zero_scale_orient(self):
        result = self._run(
            {"objectType": MagicMock(return_value="joint")},
            joint_name="joint1",
            orient=[0.0, 90.0, 0.0],
            zero_scale_orient=True,
        )
        assert result["success"] is True

    def test_joint_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, joint_name="missing")
        assert result["success"] is False

    def test_wrong_node_type(self):
        result = self._run({"objectType": MagicMock(return_value="transform")}, joint_name="pSphere1")
        assert result["success"] is False
        assert result["message"].lower().startswith("wrong node type")

    def test_exception_propagates(self):
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "joint"
        cmds_mock.setAttr.side_effect = RuntimeError("locked")
        result = self._run(
            {"objExists": cmds_mock.objExists, "objectType": cmds_mock.objectType, "setAttr": cmds_mock.setAttr},
            joint_name="joint1",
        )
        assert result["success"] is False
