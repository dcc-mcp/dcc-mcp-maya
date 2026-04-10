"""Unit tests for Round 17: maya-ocean, maya-toon, maya-paint-effects.

All tests mock maya.cmds / maya.mel to avoid requiring a real Maya environment.
Scripts are loaded via importlib to handle hyphenated skill directory names.
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
    module_name = "skill_r17_{}_{}_{}" .format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, mel_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    mel_mock = MagicMock()

    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    cmds_mock.objectType.return_value = "transform"
    cmds_mock.listRelatives.return_value = []
    cmds_mock.pluginInfo.return_value = True

    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)

    maya_mock.cmds = cmds_mock
    maya_mock.mel = mel_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.mel": mel_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }
    return maya_mock, cmds_mock, mel_mock, modules


# ---------------------------------------------------------------------------
# maya-ocean
# ---------------------------------------------------------------------------

class TestCreateOcean:
    def test_basic_success(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.polyPlane.return_value = ["ocean_plane1", "polyPlane1"]
        cmds_mock.shadingNode.return_value = "oceanShader1"
        cmds_mock.sets.return_value = "oceanShader1_SG"

        mod = _load_script("maya-ocean", "create_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.create_ocean(name="ocean", size=50.0)

        assert result["success"] is True
        assert result["context"]["ocean_shader"] == "oceanShader1"
        assert result["context"]["plane_transform"] == "ocean_plane1"
        assert "prompt" in result

    def test_low_resolution_rejected(self):
        mod = _load_script("maya-ocean", "create_ocean")
        result = mod.create_ocean(resolution=5)
        assert result["success"] is False
        assert "resolution" in result["error"].lower()

    def test_default_name(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.polyPlane.return_value = ["ocean_plane1"]
        cmds_mock.shadingNode.return_value = "oceanShader1"
        cmds_mock.sets.return_value = "ocean_SG"

        mod = _load_script("maya-ocean", "create_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.create_ocean()

        assert result["success"] is True

    def test_import_error(self):
        mod = _load_script("maya-ocean", "create_ocean")
        # Just verify module loaded correctly and function is callable
        assert callable(mod.create_ocean)

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.polyPlane.side_effect = RuntimeError("Maya error")

        mod = _load_script("maya-ocean", "create_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.create_ocean()

        assert result["success"] is False
        assert "failed" in result["message"].lower()

    def test_wave_attributes_set(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.polyPlane.return_value = ["ocean_plane1"]
        cmds_mock.shadingNode.return_value = "ocean_shader1"
        cmds_mock.sets.return_value = "ocean_SG"

        mod = _load_script("maya-ocean", "create_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.create_ocean(wave_height=2.0, wave_turbulence=0.8)

        assert result["success"] is True
        # Verify setAttr was called for wave attrs
        calls = [str(c) for c in cmds_mock.setAttr.call_args_list]
        assert any("waveHeight" in c for c in calls)
        assert any("waveTurbulence" in c for c in calls)


class TestListOceans:
    def test_empty_scene(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []

        mod = _load_script("maya-ocean", "list_oceans")
        with patch.dict(sys.modules, modules):
            result = mod.list_oceans()

        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["oceans"] == []

    def test_multiple_oceans(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["oceanShader1", "oceanShader2"]
        cmds_mock.getAttr.return_value = 1.0

        mod = _load_script("maya-ocean", "list_oceans")
        with patch.dict(sys.modules, modules):
            result = mod.list_oceans()

        assert result["success"] is True
        assert result["context"]["count"] == 2
        assert len(result["context"]["oceans"]) == 2

    def test_prompt_present(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []

        mod = _load_script("maya-ocean", "list_oceans")
        with patch.dict(sys.modules, modules):
            result = mod.list_oceans()

        assert "prompt" in result

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("ls failed")

        mod = _load_script("maya-ocean", "list_oceans")
        with patch.dict(sys.modules, modules):
            result = mod.list_oceans()

        assert result["success"] is False


class TestDeleteOcean:
    def test_basic_delete(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "oceanShader"

        mod = _load_script("maya-ocean", "delete_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.delete_ocean(name="oceanShader1")

        assert result["success"] is True
        cmds_mock.delete.assert_called()

    def test_missing_name(self):
        mod = _load_script("maya-ocean", "delete_ocean")
        result = mod.delete_ocean(name="")
        assert result["success"] is False
        assert "name" in result["error"].lower()

    def test_node_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-ocean", "delete_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.delete_ocean(name="nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_wrong_type_rejected(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"

        mod = _load_script("maya-ocean", "delete_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.delete_ocean(name="pSphere1")

        assert result["success"] is False
        assert "oceanShader" in result["message"]

    def test_delete_with_geometry(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "oceanShader"
        cmds_mock.listConnections.return_value = ["oceanShader1_SG"]
        cmds_mock.sets.return_value = ["ocean_plane1"]
        cmds_mock.listRelatives.return_value = ["ocean_plane_transform"]

        mod = _load_script("maya-ocean", "delete_ocean")
        with patch.dict(sys.modules, modules):
            result = mod.delete_ocean(name="oceanShader1", delete_geometry=True)

        assert result["success"] is True


class TestSetOceanAttribute:
    def test_scalar_attribute(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-ocean", "set_ocean_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_ocean_attribute(name="oceanShader1", attribute="waveHeight", value=2.0)

        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("oceanShader1.waveHeight", 2.0)

    def test_vector_attribute(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-ocean", "set_ocean_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_ocean_attribute(name="oceanShader1", attribute="windUV", value=[0.5, 0.5])

        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("oceanShader1.windUV", 0.5, 0.5)

    def test_missing_name(self):
        mod = _load_script("maya-ocean", "set_ocean_attribute")
        result = mod.set_ocean_attribute(name="", attribute="waveHeight", value=1.0)
        assert result["success"] is False

    def test_missing_attribute(self):
        mod = _load_script("maya-ocean", "set_ocean_attribute")
        result = mod.set_ocean_attribute(name="oceanShader1", attribute="", value=1.0)
        assert result["success"] is False

    def test_node_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-ocean", "set_ocean_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_ocean_attribute(name="missing", attribute="waveHeight", value=1.0)

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.setAttr.side_effect = RuntimeError("setAttr failed")

        mod = _load_script("maya-ocean", "set_ocean_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_ocean_attribute(name="oceanShader1", attribute="waveHeight", value=1.0)

        assert result["success"] is False


class TestCreateWake:
    def test_basic_success(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "oceanShader"
        cmds_mock.spaceLocator.return_value = ["wakeDriver_loc"]
        cmds_mock.createNode.return_value = "oceanWake1"
        cmds_mock.attributeQuery.return_value = False

        mod = _load_script("maya-ocean", "create_wake")
        with patch.dict(sys.modules, modules):
            result = mod.create_wake(ocean_shader="oceanShader1")

        assert result["success"] is True
        assert result["context"]["wake_node"] == "oceanWake1"

    def test_with_existing_object(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "oceanShader"
        cmds_mock.createNode.return_value = "oceanWake1"
        cmds_mock.attributeQuery.return_value = False

        mod = _load_script("maya-ocean", "create_wake")
        with patch.dict(sys.modules, modules):
            result = mod.create_wake(ocean_shader="oceanShader1", object_name="pSphere1")

        assert result["success"] is True
        assert result["context"]["locator"] is None

    def test_missing_ocean_shader(self):
        mod = _load_script("maya-ocean", "create_wake")
        result = mod.create_wake(ocean_shader="")
        assert result["success"] is False

    def test_ocean_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-ocean", "create_wake")
        with patch.dict(sys.modules, modules):
            result = mod.create_wake(ocean_shader="nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_wrong_node_type(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"

        mod = _load_script("maya-ocean", "create_wake")
        with patch.dict(sys.modules, modules):
            result = mod.create_wake(ocean_shader="pSphere1")

        assert result["success"] is False

    def test_time_connection_when_available(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "oceanShader"
        cmds_mock.spaceLocator.return_value = ["wakeDriver_loc"]
        cmds_mock.createNode.return_value = "oceanWake1"
        cmds_mock.attributeQuery.return_value = True  # time attr exists

        mod = _load_script("maya-ocean", "create_wake")
        with patch.dict(sys.modules, modules):
            result = mod.create_wake(ocean_shader="oceanShader1")

        assert result["success"] is True
        cmds_mock.connectAttr.assert_called()


# ---------------------------------------------------------------------------
# maya-toon
# ---------------------------------------------------------------------------

class TestCreateToonOutline:
    def test_basic_success(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["pfxToon1"]

        mod = _load_script("maya-toon", "create_toon_outline")
        with patch.dict(sys.modules, modules):
            result = mod.create_toon_outline(objects=["pSphere1"], line_width=2.0)

        assert result["success"] is True
        assert result["context"]["toon_node"] == "pfxToon1"
        assert "prompt" in result

    def test_no_objects_uses_selection(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["pfxToon1"]

        mod = _load_script("maya-toon", "create_toon_outline")
        with patch.dict(sys.modules, modules):
            result = mod.create_toon_outline()

        assert result["success"] is True

    def test_no_toon_node_created(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []  # no pfxToon nodes

        mod = _load_script("maya-toon", "create_toon_outline")
        with patch.dict(sys.modules, modules):
            result = mod.create_toon_outline(objects=["pSphere1"])

        assert result["success"] is False

    def test_custom_name(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["pfxToon1"]
        cmds_mock.rename.return_value = "myToon"

        mod = _load_script("maya-toon", "create_toon_outline")
        with patch.dict(sys.modules, modules):
            result = mod.create_toon_outline(objects=["pSphere1"], name="myToon")

        assert result["success"] is True

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.side_effect = RuntimeError("MEL error")

        mod = _load_script("maya-toon", "create_toon_outline")
        with patch.dict(sys.modules, modules):
            result = mod.create_toon_outline(objects=["pSphere1"])

        assert result["success"] is False


class TestListToonLines:
    def test_empty_scene(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []

        mod = _load_script("maya-toon", "list_toon_lines")
        with patch.dict(sys.modules, modules):
            result = mod.list_toon_lines()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_multiple_nodes(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["pfxToon1", "pfxToon2"]
        cmds_mock.getAttr.return_value = 1.0

        mod = _load_script("maya-toon", "list_toon_lines")
        with patch.dict(sys.modules, modules):
            result = mod.list_toon_lines()

        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("ls failed")

        mod = _load_script("maya-toon", "list_toon_lines")
        with patch.dict(sys.modules, modules):
            result = mod.list_toon_lines()

        assert result["success"] is False


class TestDeleteToonLine:
    def test_basic_delete(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "pfxToon"

        mod = _load_script("maya-toon", "delete_toon_line")
        with patch.dict(sys.modules, modules):
            result = mod.delete_toon_line(name="pfxToon1")

        assert result["success"] is True
        cmds_mock.delete.assert_called_with("pfxToon1")

    def test_missing_name(self):
        mod = _load_script("maya-toon", "delete_toon_line")
        result = mod.delete_toon_line(name="")
        assert result["success"] is False

    def test_node_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-toon", "delete_toon_line")
        with patch.dict(sys.modules, modules):
            result = mod.delete_toon_line(name="nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_wrong_type_rejected(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"

        mod = _load_script("maya-toon", "delete_toon_line")
        with patch.dict(sys.modules, modules):
            result = mod.delete_toon_line(name="pSphere1")

        assert result["success"] is False
        assert "pfxToon" in result["message"]

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "pfxToon"
        cmds_mock.delete.side_effect = RuntimeError("delete failed")

        mod = _load_script("maya-toon", "delete_toon_line")
        with patch.dict(sys.modules, modules):
            result = mod.delete_toon_line(name="pfxToon1")

        assert result["success"] is False


class TestSetToonAttribute:
    def test_scalar_attribute(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-toon", "set_toon_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_toon_attribute(name="pfxToon1", attribute="profileLineWidth", value=3.0)

        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("pfxToon1.profileLineWidth", 3.0)

    def test_color_attribute(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-toon", "set_toon_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_toon_attribute(
                name="pfxToon1", attribute="profileLineColor", value=[1.0, 0.0, 0.0]
            )

        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("pfxToon1.profileLineColor", 1.0, 0.0, 0.0)

    def test_missing_name(self):
        mod = _load_script("maya-toon", "set_toon_attribute")
        result = mod.set_toon_attribute(name="", attribute="profileLineWidth", value=1.0)
        assert result["success"] is False

    def test_missing_attribute(self):
        mod = _load_script("maya-toon", "set_toon_attribute")
        result = mod.set_toon_attribute(name="pfxToon1", attribute="", value=1.0)
        assert result["success"] is False

    def test_node_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-toon", "set_toon_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_toon_attribute(name="missing", attribute="profileLineWidth", value=1.0)

        assert result["success"] is False

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.setAttr.side_effect = RuntimeError("setAttr failed")

        mod = _load_script("maya-toon", "set_toon_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_toon_attribute(name="pfxToon1", attribute="profileLineWidth", value=1.0)

        assert result["success"] is False


class TestAssignToonShader:
    def test_basic_success(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.shadingNode.return_value = "toonSurface1"
        cmds_mock.sets.return_value = "toonSurface1_SG"
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-toon", "assign_toon_shader")
        with patch.dict(sys.modules, modules):
            result = mod.assign_toon_shader(objects=["pSphere1"])

        assert result["success"] is True
        assert result["context"]["shader"] == "toonSurface1"
        assert "prompt" in result

    def test_empty_objects(self):
        mod = _load_script("maya-toon", "assign_toon_shader")
        result = mod.assign_toon_shader(objects=[])
        assert result["success"] is False

    def test_invalid_color_length(self):
        mod = _load_script("maya-toon", "assign_toon_shader")
        result = mod.assign_toon_shader(objects=["pSphere1"], color=[1.0, 0.0])
        assert result["success"] is False
        assert "color" in result["message"].lower()

    def test_missing_object(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.shadingNode.return_value = "toonSurface1"
        cmds_mock.sets.return_value = "toonSurface1_SG"
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-toon", "assign_toon_shader")
        with patch.dict(sys.modules, modules):
            result = mod.assign_toon_shader(objects=["nonexistent"])

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_custom_name(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.shadingNode.return_value = "myToon"
        cmds_mock.sets.return_value = "myToon_SG"
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-toon", "assign_toon_shader")
        with patch.dict(sys.modules, modules):
            result = mod.assign_toon_shader(objects=["pSphere1"], name="myToon")

        assert result["success"] is True

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.shadingNode.side_effect = RuntimeError("shadingNode failed")

        mod = _load_script("maya-toon", "assign_toon_shader")
        with patch.dict(sys.modules, modules):
            result = mod.assign_toon_shader(objects=["pSphere1"])

        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-paint-effects
# ---------------------------------------------------------------------------

class TestCreateStroke:
    def test_basic_success(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["stroke1"]
        cmds_mock.listRelatives.return_value = ["stroke1Transform"]

        mod = _load_script("maya-paint-effects", "create_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.create_stroke(position=[0.0, 0.0, 0.0])

        assert result["success"] is True
        assert result["context"]["stroke_node"] == "stroke1"
        assert "prompt" in result

    def test_invalid_position_length(self):
        mod = _load_script("maya-paint-effects", "create_stroke")
        result = mod.create_stroke(position=[0.0, 1.0])
        assert result["success"] is False
        assert "position" in result["message"].lower()

    def test_no_stroke_created(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []  # no stroke nodes

        mod = _load_script("maya-paint-effects", "create_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.create_stroke(position=[0.0, 0.0, 0.0])

        assert result["success"] is False

    def test_with_brush_path(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["stroke1"]
        cmds_mock.listRelatives.return_value = ["stroke1Transform"]

        mod = _load_script("maya-paint-effects", "create_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.create_stroke(brush_path="/maya/brushes/roses.mel")

        assert result["success"] is True
        mel_mock.eval.assert_any_call('source "/maya/brushes/roses.mel"')

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.side_effect = RuntimeError("MEL error")

        mod = _load_script("maya-paint-effects", "create_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.create_stroke()

        assert result["success"] is False


class TestListStrokes:
    def test_empty_scene(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []

        mod = _load_script("maya-paint-effects", "list_strokes")
        with patch.dict(sys.modules, modules):
            result = mod.list_strokes()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_multiple_strokes(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["stroke1", "stroke2"]
        cmds_mock.listRelatives.return_value = ["stroke1Transform"]
        cmds_mock.getAttr.side_effect = Exception("attr missing")

        mod = _load_script("maya-paint-effects", "list_strokes")
        with patch.dict(sys.modules, modules):
            result = mod.list_strokes()

        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_prompt_present(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []

        mod = _load_script("maya-paint-effects", "list_strokes")
        with patch.dict(sys.modules, modules):
            result = mod.list_strokes()

        assert "prompt" in result

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("ls failed")

        mod = _load_script("maya-paint-effects", "list_strokes")
        with patch.dict(sys.modules, modules):
            result = mod.list_strokes()

        assert result["success"] is False


class TestDeleteStroke:
    def test_basic_delete_transform(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "stroke"
        cmds_mock.listRelatives.return_value = ["stroke1Transform"]

        mod = _load_script("maya-paint-effects", "delete_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.delete_stroke(name="stroke1")

        assert result["success"] is True
        cmds_mock.delete.assert_called_with("stroke1Transform")

    def test_delete_transform_node(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"

        mod = _load_script("maya-paint-effects", "delete_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.delete_stroke(name="stroke1Transform")

        assert result["success"] is True
        cmds_mock.delete.assert_called_with("stroke1Transform")

    def test_missing_name(self):
        mod = _load_script("maya-paint-effects", "delete_stroke")
        result = mod.delete_stroke(name="")
        assert result["success"] is False

    def test_node_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-paint-effects", "delete_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.delete_stroke(name="nonexistent")

        assert result["success"] is False

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "stroke"
        cmds_mock.listRelatives.return_value = ["stroke1Transform"]
        cmds_mock.delete.side_effect = RuntimeError("delete failed")

        mod = _load_script("maya-paint-effects", "delete_stroke")
        with patch.dict(sys.modules, modules):
            result = mod.delete_stroke(name="stroke1")

        assert result["success"] is False


class TestSetBrushAttribute:
    def test_scalar_attribute(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-paint-effects", "set_brush_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_brush_attribute(name="stroke1", attribute="brush.globalScale", value=2.0)

        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("stroke1.brush.globalScale", 2.0)

    def test_color_attribute(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True

        mod = _load_script("maya-paint-effects", "set_brush_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_brush_attribute(
                name="stroke1", attribute="brush.color1", value=[0.0, 1.0, 0.0]
            )

        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("stroke1.brush.color1", 0.0, 1.0, 0.0)

    def test_missing_name(self):
        mod = _load_script("maya-paint-effects", "set_brush_attribute")
        result = mod.set_brush_attribute(name="", attribute="brush.globalScale", value=1.0)
        assert result["success"] is False

    def test_missing_attribute(self):
        mod = _load_script("maya-paint-effects", "set_brush_attribute")
        result = mod.set_brush_attribute(name="stroke1", attribute="", value=1.0)
        assert result["success"] is False

    def test_node_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-paint-effects", "set_brush_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_brush_attribute(name="missing", attribute="brush.globalScale", value=1.0)

        assert result["success"] is False

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.setAttr.side_effect = RuntimeError("setAttr failed")

        mod = _load_script("maya-paint-effects", "set_brush_attribute")
        with patch.dict(sys.modules, modules):
            result = mod.set_brush_attribute(name="stroke1", attribute="brush.globalScale", value=1.0)

        assert result["success"] is False


class TestConvertStrokeToPoly:
    def test_basic_success(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.ls.return_value = ["strokePoly1"]

        mod = _load_script("maya-paint-effects", "convert_stroke_to_poly")
        with patch.dict(sys.modules, modules):
            result = mod.convert_stroke_to_poly(name="stroke1Transform")

        assert result["success"] is True
        assert result["context"]["poly_mesh"] == "strokePoly1"
        assert "prompt" in result

    def test_missing_name(self):
        mod = _load_script("maya-paint-effects", "convert_stroke_to_poly")
        result = mod.convert_stroke_to_poly(name="")
        assert result["success"] is False

    def test_node_not_found(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False

        mod = _load_script("maya-paint-effects", "convert_stroke_to_poly")
        with patch.dict(sys.modules, modules):
            result = mod.convert_stroke_to_poly(name="nonexistent")

        assert result["success"] is False

    def test_no_mesh_produced(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.ls.return_value = []  # no selection after conversion

        mod = _load_script("maya-paint-effects", "convert_stroke_to_poly")
        with patch.dict(sys.modules, modules):
            result = mod.convert_stroke_to_poly(name="stroke1Transform")

        assert result["success"] is False
        assert "conversion produced no mesh" in result["message"].lower()

    def test_triangle_output(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.ls.return_value = ["strokePoly1"]

        mod = _load_script("maya-paint-effects", "convert_stroke_to_poly")
        with patch.dict(sys.modules, modules):
            result = mod.convert_stroke_to_poly(name="stroke1Transform", quad_output=False)

        assert result["success"] is True
        assert result["context"]["quad_output"] is False
        # Verify MEL call uses flag 0
        mel_calls = [str(c) for c in mel_mock.eval.call_args_list]
        assert any("0)" in c for c in mel_calls)

    def test_exception_handling(self):
        maya_mock, cmds_mock, mel_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        mel_mock.eval.side_effect = RuntimeError("MEL error")

        mod = _load_script("maya-paint-effects", "convert_stroke_to_poly")
        with patch.dict(sys.modules, modules):
            result = mod.convert_stroke_to_poly(name="stroke1Transform")

        assert result["success"] is False
