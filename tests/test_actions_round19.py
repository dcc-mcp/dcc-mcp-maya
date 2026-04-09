"""Round 19 tests: wire_deformer, sculpt_deformer, dynamics (nucleus + fields)."""

# Import built-in modules
import sys
from typing import Any
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Patch maya.cmds for all tests in this module."""
    cmds = MagicMock()

    # wire_deformer defaults
    cmds.objExists.return_value = True
    cmds.wire.return_value = ["wire1"]
    cmds.sculpt.return_value = ["sculpt1", "sculpt1Handle", "sculpt1OriginShape"]

    # dynamics defaults
    cmds.createNode.return_value = "nucleus1"
    cmds.ls.return_value = ["time1"]
    cmds.objectType.return_value = "nucleus"
    cmds.isConnected.return_value = False
    cmds.getAttr.return_value = 9.8
    cmds.gravity.return_value = ["gravityField1"]
    cmds.turbulence.return_value = ["turbulenceField1"]
    cmds.radial.return_value = ["radialField1"]

    maya_mock = MagicMock()
    maya_mock.cmds = cmds
    monkeypatch.setitem(sys.modules, "maya", maya_mock)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    return cmds


# ---------------------------------------------------------------------------
# wire_deformer
# ---------------------------------------------------------------------------

class TestWireDeformer:
    def test_basic(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        mock_maya.wire.return_value = ["wire1"]
        result = wire_deformer(curves=["curve1"], objects=["pSphere1"])
        assert result["success"] is True
        assert result["context"]["wire_node"] == "wire1"
        assert "curve1" in result["context"]["curves"]
        assert "pSphere1" in result["context"]["objects"]

    def test_dropoff_distance(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        result = wire_deformer(curves=["curve1"], objects=["pSphere1"], dropoff_distance=50.0)
        assert result["success"] is True
        assert result["context"]["dropoff_distance"] == 50.0

    def test_no_curves_error(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        result = wire_deformer(curves=[], objects=["pSphere1"])
        assert result["success"] is False
        assert "No curves" in result["message"]

    def test_no_objects_error(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        result = wire_deformer(curves=["curve1"], objects=[])
        assert result["success"] is False
        assert "No objects" in result["message"]

    def test_missing_curve(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        def exists_side_effect(name):
            return name != "missingCurve"

        mock_maya.objExists.side_effect = exists_side_effect
        result = wire_deformer(curves=["missingCurve"], objects=["pSphere1"])
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_missing_object(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        def exists_side_effect(name):
            return name != "missingMesh"

        mock_maya.objExists.side_effect = exists_side_effect
        result = wire_deformer(curves=["curve1"], objects=["missingMesh"])
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_with_name(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        mock_maya.wire.return_value = ["myWire"]
        result = wire_deformer(curves=["curve1"], objects=["pSphere1"], name="myWire")
        assert result["success"] is True
        assert result["context"]["wire_node"] == "myWire"

    def test_import_error(self, monkeypatch):
        from dcc_mcp_maya.actions.deformer_advanced import wire_deformer

        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            monkeypatch.delitem(sys.modules, "maya", raising=False)
            monkeypatch.delitem(sys.modules, "maya.cmds", raising=False)
            result = wire_deformer(curves=["curve1"], objects=["pSphere1"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# sculpt_deformer
# ---------------------------------------------------------------------------

class TestSculptDeformer:
    def test_basic_stretch(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        result = sculpt_deformer(objects=["pSphere1"])
        assert result["success"] is True
        assert result["context"]["sculpt_node"] == "sculpt1"
        assert result["context"]["mode"] == "stretch"

    def test_project_mode(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        result = sculpt_deformer(objects=["pSphere1"], mode="project")
        assert result["success"] is True
        assert result["context"]["mode"] == "project"

    def test_flip_mode(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        result = sculpt_deformer(objects=["pSphere1"], mode="flip")
        assert result["success"] is True
        assert result["context"]["mode"] == "flip"

    def test_invalid_mode(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        result = sculpt_deformer(objects=["pSphere1"], mode="invalid")
        assert result["success"] is False
        assert "Invalid mode" in result["message"]

    def test_no_objects_error(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        result = sculpt_deformer(objects=[])
        assert result["success"] is False
        assert "No objects" in result["message"]

    def test_missing_object(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        mock_maya.objExists.return_value = False
        result = sculpt_deformer(objects=["missingMesh"])
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_max_displacement(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        result = sculpt_deformer(objects=["pSphere1"], max_displacement=5.0)
        assert result["success"] is True
        assert result["context"]["max_displacement"] == 5.0

    def test_with_name(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        mock_maya.sculpt.return_value = ["mySculpt", "mySculptHandle", "mySculptOrigin"]
        result = sculpt_deformer(objects=["pSphere1"], name="mySculpt")
        assert result["success"] is True
        assert result["context"]["sculpt_node"] == "mySculpt"

    def test_returns_sphere_and_origin(self, mock_maya):
        from dcc_mcp_maya.actions.deformer_advanced import sculpt_deformer

        result = sculpt_deformer(objects=["pSphere1"])
        assert result["context"]["sculpt_sphere"] == "sculpt1Handle"
        assert result["context"]["sculpt_origin"] == "sculpt1OriginShape"


# ---------------------------------------------------------------------------
# create_nucleus
# ---------------------------------------------------------------------------

class TestCreateNucleus:
    def test_basic(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_nucleus

        mock_maya.createNode.return_value = "nucleus1"
        result = create_nucleus()
        assert result["success"] is True
        assert result["context"]["nucleus_node"] == "nucleus1"
        assert result["context"]["gravity"] == -9.8

    def test_custom_gravity(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_nucleus

        result = create_nucleus(gravity=-15.0)
        assert result["success"] is True
        assert result["context"]["gravity"] == -15.0

    def test_with_name(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_nucleus

        mock_maya.createNode.return_value = "myNucleus"
        result = create_nucleus(name="myNucleus")
        assert result["success"] is True
        assert result["context"]["nucleus_node"] == "myNucleus"

    def test_wind_speed(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_nucleus

        result = create_nucleus(wind_speed=5.0, wind_direction=[1.0, 0.0, 0.0])
        assert result["success"] is True
        assert result["context"]["wind_speed"] == 5.0

    def test_default_wind_direction(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_nucleus

        result = create_nucleus()
        assert result["context"]["wind_direction"] == [0.0, 0.0, 1.0]

    def test_already_connected(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_nucleus

        mock_maya.isConnected.return_value = True
        result = create_nucleus()
        assert result["success"] is True
        mock_maya.connectAttr.assert_not_called()

    def test_import_error(self, monkeypatch):
        from dcc_mcp_maya.actions.dynamics import create_nucleus

        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            monkeypatch.delitem(sys.modules, "maya", raising=False)
            monkeypatch.delitem(sys.modules, "maya.cmds", raising=False)
            result = create_nucleus()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# set_nucleus_attribute
# ---------------------------------------------------------------------------

class TestSetNucleusAttribute:
    def test_scalar_attr(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import set_nucleus_attribute

        mock_maya.objectType.return_value = "nucleus"
        mock_maya.objExists.return_value = True
        result = set_nucleus_attribute("nucleus1", "gravity", -15.0)
        assert result["success"] is True
        assert result["context"]["attribute"] == "gravity"
        assert result["context"]["value"] == -15.0

    def test_triple_attr(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import set_nucleus_attribute

        mock_maya.objectType.return_value = "nucleus"
        result = set_nucleus_attribute("nucleus1", "windDirection", [1.0, 0.0, 0.0])
        assert result["success"] is True

    def test_node_not_found(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import set_nucleus_attribute

        mock_maya.objExists.return_value = False
        result = set_nucleus_attribute("missingNucleus", "gravity", -9.8)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_wrong_node_type(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import set_nucleus_attribute

        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "transform"
        result = set_nucleus_attribute("pSphere1", "gravity", -9.8)
        assert result["success"] is False
        assert "Not a nucleus" in result["message"]

    def test_attribute_not_found(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import set_nucleus_attribute

        mock_maya.objectType.return_value = "nucleus"

        def exists_side_effect(name):
            if "." in str(name):
                return False
            return True

        mock_maya.objExists.side_effect = exists_side_effect
        result = set_nucleus_attribute("nucleus1", "nonExistentAttr", 1.0)
        assert result["success"] is False
        assert "Attribute not found" in result["message"]

    def test_integer_value(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import set_nucleus_attribute

        mock_maya.objectType.return_value = "nucleus"
        result = set_nucleus_attribute("nucleus1", "substeps", 3)
        assert result["success"] is True
        assert result["context"]["value"] == 3


# ---------------------------------------------------------------------------
# create_dynamic_field
# ---------------------------------------------------------------------------

class TestCreateDynamicField:
    def test_gravity_field(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        mock_maya.gravity.return_value = ["gravityField1"]
        result = create_dynamic_field(field_type="gravity", magnitude=9.8)
        assert result["success"] is True
        assert result["context"]["field_type"] == "gravity"
        assert result["context"]["field_node"] == "gravityField1"

    def test_turbulence_field(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        mock_maya.turbulence.return_value = ["turbulenceField1"]
        result = create_dynamic_field(field_type="turbulence", magnitude=2.0)
        assert result["success"] is True
        assert result["context"]["field_type"] == "turbulence"

    def test_radial_field(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        mock_maya.radial.return_value = ["radialField1"]
        result = create_dynamic_field(field_type="radial")
        assert result["success"] is True

    def test_invalid_field_type(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        result = create_dynamic_field(field_type="invalid")
        assert result["success"] is False
        assert "Invalid field type" in result["message"]

    def test_connect_to_objects(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        mock_maya.gravity.return_value = ["gravityField1"]
        mock_maya.objExists.return_value = True
        mock_maya.objExists.side_effect = lambda n: True
        result = create_dynamic_field(field_type="gravity", objects=["particle1"])
        assert result["success"] is True
        assert "particle1" in result["context"]["connected_objects"]
        mock_maya.connectDynamic.assert_called_once()

    def test_missing_object_error(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        def exists_side_effect(name):
            return name != "missingParticle"

        mock_maya.objExists.side_effect = exists_side_effect
        mock_maya.gravity.return_value = ["gravityField1"]
        result = create_dynamic_field(field_type="gravity", objects=["missingParticle"])
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_no_objects(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        mock_maya.gravity.return_value = ["gravityField1"]
        result = create_dynamic_field(field_type="gravity")
        assert result["success"] is True
        assert result["context"]["connected_objects"] == []

    def test_magnitude_attribute_missing(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        mock_maya.gravity.return_value = ["gravityField1"]
        mock_maya.objExists.side_effect = lambda name: "." not in str(name)
        result = create_dynamic_field(field_type="gravity", magnitude=5.0)
        assert result["success"] is True

    def test_import_error(self, monkeypatch):
        from dcc_mcp_maya.actions.dynamics import create_dynamic_field

        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            monkeypatch.delitem(sys.modules, "maya", raising=False)
            monkeypatch.delitem(sys.modules, "maya.cmds", raising=False)
            result = create_dynamic_field(field_type="gravity")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# connect_field_to_objects
# ---------------------------------------------------------------------------

class TestConnectFieldToObjects:
    def test_basic(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import connect_field_to_objects

        mock_maya.objExists.return_value = True
        result = connect_field_to_objects("gravityField1", ["particle1", "particle2"])
        assert result["success"] is True
        assert "particle1" in result["context"]["connected_objects"]
        mock_maya.connectDynamic.assert_called_once()

    def test_no_objects_error(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import connect_field_to_objects

        result = connect_field_to_objects("gravityField1", [])
        assert result["success"] is False
        assert "No objects" in result["message"]

    def test_field_not_found(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import connect_field_to_objects

        mock_maya.objExists.return_value = False
        result = connect_field_to_objects("missingField", ["particle1"])
        assert result["success"] is False
        assert "Field node not found" in result["message"]

    def test_missing_object(self, mock_maya):
        from dcc_mcp_maya.actions.dynamics import connect_field_to_objects

        def exists_side_effect(name):
            return name != "missingParticle"

        mock_maya.objExists.side_effect = exists_side_effect
        result = connect_field_to_objects("gravityField1", ["missingParticle"])
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_import_error(self, monkeypatch):
        from dcc_mcp_maya.actions.dynamics import connect_field_to_objects

        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            monkeypatch.delitem(sys.modules, "maya", raising=False)
            monkeypatch.delitem(sys.modules, "maya.cmds", raising=False)
            result = connect_field_to_objects("gravityField1", ["particle1"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# register_all coverage
# ---------------------------------------------------------------------------

class TestRegisterAllRound19:
    def test_new_actions_in_all(self):
        import dcc_mcp_maya.actions as actions_pkg

        for name in (
            "wire_deformer",
            "sculpt_deformer",
            "create_nucleus",
            "set_nucleus_attribute",
            "create_dynamic_field",
            "connect_field_to_objects",
        ):
            assert name in actions_pkg.__all__, "{} missing from __all__".format(name)

    def test_register_all_count(self):
        import dcc_mcp_maya.actions as actions_pkg

        registry = MagicMock()
        actions_pkg.register_all(registry)
        assert registry.register.call_count >= 174
