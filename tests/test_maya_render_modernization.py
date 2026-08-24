"""Behavior regressions for the typed Maya rendering vocabulary."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, call, patch

import yaml
from conftest import load_and_call

SKILLS_ROOT = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills"


class _FakeAOVInterface:
    nodes = {}

    def addAOV(self, name, aovType=None):
        node = "aiAOV_{}".format(name)
        self.nodes[name] = {"node": node, "type": aovType or "rgba", "enabled": True}
        return node

    def getAOVNodes(self, names=False):
        pairs = [(name, data["node"]) for name, data in sorted(self.nodes.items())]
        return pairs if names else [node for _name, node in pairs]

    def removeAOV(self, name):
        return self.nodes.pop(name, None) is not None


def _call_set_aov(cmds, **kwargs):
    maya = ModuleType("maya")
    maya.cmds = cmds
    mtoa = ModuleType("mtoa")
    aovs = ModuleType("mtoa.aovs")
    aovs.AOVInterface = _FakeAOVInterface
    aovs.TYPES = (("float", 4), ("rgb", 5), ("rgba", 6), ("vector", 7))
    mtoa.aovs = aovs

    path = SKILLS_ROOT / "maya-render" / "scripts" / "set_aov.py"
    spec = importlib.util.spec_from_file_location("maya_render_set_aov_test", str(path))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {"maya": maya, "maya.cmds": cmds, "mtoa": mtoa, "mtoa.aovs": aovs},
    ):
        spec.loader.exec_module(module)
        return module.main(**kwargs)


def test_set_aov_add_returns_exact_native_round_trip():
    _FakeAOVInterface.nodes = {}
    cmds = MagicMock()
    cmds.pluginInfo.side_effect = [False, True]

    def _get_attr(attr):
        node, field = attr.rsplit(".", 1)
        data = next(value for value in _FakeAOVInterface.nodes.values() if value["node"] == node)
        return data[field]

    cmds.getAttr.side_effect = _get_attr

    result = _call_set_aov(cmds, action="add", name="diffuse", data_type="rgba")

    assert result["success"] is True, result
    assert result["context"]["action"] == "add"
    assert result["context"]["aovs"] == [
        {"name": "diffuse", "node": "aiAOV_diffuse", "data_type": "rgba", "enabled": True}
    ]
    cmds.loadPlugin.assert_called_once_with("mtoa", quiet=True)


def test_set_aov_list_is_sorted_and_read_only():
    _FakeAOVInterface.nodes = {
        "Z": {"node": "aiAOV_Z", "type": "float", "enabled": True},
        "diffuse": {"node": "aiAOV_diffuse", "type": "rgba", "enabled": True},
    }
    cmds = MagicMock()
    cmds.pluginInfo.return_value = True

    def _get_attr(attr):
        node, field = attr.rsplit(".", 1)
        data = next(value for value in _FakeAOVInterface.nodes.values() if value["node"] == node)
        return data[field]

    cmds.getAttr.side_effect = _get_attr

    result = _call_set_aov(cmds, action="list")

    assert result["success"] is True, result
    assert [item["name"] for item in result["context"]["aovs"]] == ["Z", "diffuse"]
    assert result["context"]["changed"] is False
    assert _FakeAOVInterface.nodes["Z"]["node"] == "aiAOV_Z"


def test_set_aov_maps_native_arnold_type_codes_to_stable_names():
    _FakeAOVInterface.nodes = {
        "diffuse": {"node": "aiAOV_diffuse", "type": 6, "enabled": True},
    }
    cmds = MagicMock()
    cmds.pluginInfo.return_value = True

    def _get_attr(attr):
        node, field = attr.rsplit(".", 1)
        data = next(value for value in _FakeAOVInterface.nodes.values() if value["node"] == node)
        return data[field]

    cmds.getAttr.side_effect = _get_attr

    result = _call_set_aov(cmds, action="list")

    assert result["success"] is True, result
    assert result["context"]["aovs"][0]["data_type"] == "rgba"


def test_set_aov_add_rolls_back_when_native_state_does_not_match():
    _FakeAOVInterface.nodes = {}
    cmds = MagicMock()
    cmds.pluginInfo.return_value = True

    def _get_attr(attr):
        _node, field = attr.rsplit(".", 1)
        if field == "type":
            return 4
        return True

    cmds.getAttr.side_effect = _get_attr

    result = _call_set_aov(cmds, action="add", name="diffuse", data_type="rgba")

    assert result["success"] is False
    assert _FakeAOVInterface.nodes == {}


def test_set_aov_remove_verifies_the_named_aov_is_absent():
    _FakeAOVInterface.nodes = {
        "diffuse": {"node": "aiAOV_diffuse", "type": "rgba", "enabled": True},
    }
    cmds = MagicMock()
    cmds.pluginInfo.return_value = True
    cmds.getAttr.side_effect = lambda attr: _FakeAOVInterface.nodes["diffuse"][attr.rsplit(".", 1)[1]]

    result = _call_set_aov(cmds, action="remove", name="diffuse")

    assert result["success"] is True, result
    assert result["context"]["action"] == "remove"
    assert result["context"]["removed"]["name"] == "diffuse"
    assert result["context"]["aovs"] == []
    assert _FakeAOVInterface.nodes == {}


def test_set_exposure_reads_back_the_exact_camera_value():
    cmds = MagicMock()
    state = {"shotCamShape.aiExposure": 0.0}
    cmds.objExists.return_value = True
    cmds.nodeType.side_effect = lambda node: "camera" if node == "shotCamShape" else "transform"
    cmds.listRelatives.return_value = ["shotCamShape"]
    cmds.attributeQuery.return_value = True
    cmds.getAttr.side_effect = lambda attr: state[attr]
    cmds.setAttr.side_effect = lambda attr, value: state.__setitem__(attr, value)

    result = load_and_call(
        "maya-render/scripts/set_exposure.py",
        cmds,
        "main",
        target="shotCam",
        exposure=2.0,
    )

    assert result["success"] is True, result
    assert result["context"]["target"] == "shotCam"
    assert result["context"]["node"] == "shotCamShape"
    assert result["context"]["node_type"] == "camera"
    assert result["context"]["previous_exposure"] == 0.0
    assert result["context"]["exposure"] == 2.0


def test_set_exposure_rolls_back_when_native_readback_mismatches():
    cmds = MagicMock()
    state = {"shotCamShape.aiExposure": 0.0}
    cmds.objExists.return_value = True
    cmds.nodeType.side_effect = lambda node: "camera" if node == "shotCamShape" else "transform"
    cmds.listRelatives.return_value = ["shotCamShape"]
    cmds.attributeQuery.return_value = True
    cmds.getAttr.side_effect = lambda attr: state[attr]

    def _set_attr(attr, value):
        state[attr] = 1.5 if value == 2.0 else value

    cmds.setAttr.side_effect = _set_attr

    result = load_and_call(
        "maya-render/scripts/set_exposure.py",
        cmds,
        "main",
        target="shotCam",
        exposure=2.0,
    )

    assert result["success"] is False
    assert state["shotCamShape.aiExposure"] == 0.0


def test_render_modernization_tools_are_typed_and_discoverable():
    manifest = yaml.safe_load((SKILLS_ROOT / "maya-render" / "tools.yaml").read_text(encoding="utf-8"))
    tools = {item["name"]: item for item in manifest["tools"]}

    assert tools["set_aov"]["input_schema"]["properties"]["action"]["enum"] == [
        "add",
        "list",
        "remove",
    ]
    assert tools["set_aov"]["output_schema"]["required"] == ["action", "changed", "aovs", "count"]
    assert tools["set_aov"]["affinity"] == "main"
    assert tools["set_exposure"]["input_schema"]["properties"]["exposure"]["minimum"] == -20.0
    assert tools["set_exposure"]["output_schema"]["required"] == [
        "target",
        "node",
        "node_type",
        "previous_exposure",
        "exposure",
        "verified",
    ]
    assert tools["set_exposure"]["affinity"] == "main"
    assert tools["render_frame"]["output_schema"]["required"] == [
        "renderer",
        "view_transform",
        "camera",
        "frame",
        "width",
        "height",
        "path",
        "output_path",
        "output_size",
        "log_summary",
    ]
    assert tools["configure_color_management"]["output_schema"]["required"] == [
        "config_file_path",
        "rendering_space_name",
        "display_name",
        "view_name",
        "ocio_v2_enabled",
        "output_transform_enabled",
        "input_color_spaces",
        "rendering_spaces",
        "output_transforms",
    ]
    assert tools["set_render_settings"]["input_schema"]["properties"]["aa_samples"] == {
        "type": "integer",
        "minimum": 0,
        "maximum": 20,
    }
    assert tools["set_render_settings"]["output_schema"]["properties"]["verified"]["const"] is True

    light_manifest = yaml.safe_load((SKILLS_ROOT / "maya-light-rig" / "tools.yaml").read_text(encoding="utf-8"))
    light_tools = {item["name"]: item for item in light_manifest["tools"]}
    assert light_tools["create_three_point_rig"]["input_schema"]["properties"]["arnold_exposure"] == {
        "type": "number",
        "minimum": -20.0,
        "maximum": 20.0,
        "default": 3.0,
    }
    assert "lights" in light_tools["create_three_point_rig"]["output_schema"]["required"]


def test_configure_color_management_returns_bounded_native_enumeration(tmp_path):
    config = tmp_path / "studio.ocio"
    config.write_text("ocio_profile_version: 2.4\n", encoding="utf-8")
    cmds = MagicMock()
    values = {
        "configFilePath": str(config.resolve()),
        "renderingSpaceName": "ACEScg",
        "displayName": "Rec.1886 Rec.709 - Display",
        "viewName": "ACES 1.0 - SDR Video",
        "ociov2Enabled": True,
        "outputTransformEnabled": True,
        "inputColorSpaceNames": ["ACEScg", "sRGB", "Raw"],
        "renderingSpaceNames": ["ACEScg"],
        "outputTransformNames": ["Raw", "ACES 1.0 - SDR Video"],
    }

    def _prefs(**kwargs):
        if not kwargs.get("query"):
            return None
        return next((value for key, value in values.items() if kwargs.get(key)), None)

    cmds.colorManagementPrefs.side_effect = _prefs
    result = load_and_call(
        "maya-render/scripts/configure_color_management.py",
        cmds,
        "main",
        config_file_path=str(config),
    )

    assert result["success"] is True, result
    assert result["context"]["input_color_spaces"] == ["ACEScg", "Raw", "sRGB"]
    assert result["context"]["rendering_spaces"] == ["ACEScg"]
    assert result["context"]["output_transforms"] == ["ACES 1.0 - SDR Video", "Raw"]


def test_three_point_rig_applies_and_reads_back_arnold_exposure():
    cmds = MagicMock()
    attrs = {}
    cmds.group.return_value = "lookdevRig"
    cmds.createNode.side_effect = lambda _node_type, name, parent: name
    cmds.shadingNode.side_effect = lambda _node_type, **kwargs: kwargs["name"]
    cmds.listRelatives.side_effect = lambda transform, **_kwargs: ["{}_Shape".format(transform)]
    cmds.attributeQuery.return_value = True

    def _set_attr(attr, *values, **_kwargs):
        if len(values) == 1:
            attrs[attr] = values[0]

    cmds.setAttr.side_effect = _set_attr
    cmds.getAttr.side_effect = lambda attr: attrs[attr]

    result = load_and_call(
        "maya-light-rig/scripts/create_three_point_rig.py",
        cmds,
        "main",
        name="lookdevRig",
        arnold_exposure=3.0,
    )

    assert result["success"] is True, result
    assert result["context"]["arnold_exposure"] == 3.0
    assert [item["exposure"] for item in result["context"]["lights"]] == [3.0, 3.0, 3.0]
    assert attrs["lookdevRig_key_Shape.aiExposure"] == 3.0
    assert attrs["lookdevRig_fill_Shape.aiExposure"] == 3.0
    assert attrs["lookdevRig_rim_Shape.aiExposure"] == 3.0


def test_three_point_rig_loads_mtoa_before_creating_arnold_exposure_attributes():
    cmds = MagicMock()
    attrs = {}
    cmds.pluginInfo.side_effect = [False, True]
    cmds.group.return_value = "lookdevRig"
    cmds.createNode.side_effect = lambda _node_type, name, parent: name
    cmds.shadingNode.side_effect = lambda _node_type, **kwargs: kwargs["name"]
    cmds.listRelatives.side_effect = lambda transform, **_kwargs: ["{}_Shape".format(transform)]
    cmds.attributeQuery.return_value = True

    def _set_attr(attr, *values, **_kwargs):
        if len(values) == 1:
            attrs[attr] = values[0]

    cmds.setAttr.side_effect = _set_attr
    cmds.getAttr.side_effect = lambda attr: attrs[attr]

    result = load_and_call(
        "maya-light-rig/scripts/create_three_point_rig.py",
        cmds,
        "main",
        name="lookdevRig",
    )

    assert result["success"] is True, result
    cmds.loadPlugin.assert_called_once_with("mtoa", quiet=True)
    assert cmds.mock_calls.index(call.loadPlugin("mtoa", quiet=True)) < cmds.mock_calls.index(
        call.group(empty=True, name="lookdevRig")
    )


def test_set_render_settings_round_trips_renderer_resolution_and_sampling():
    cmds = MagicMock()
    state = {
        "defaultRenderGlobals.currentRenderer": "mayaSoftware",
        "defaultResolution.width": 640,
        "defaultResolution.height": 360,
        "defaultArnoldRenderOptions.AASamples": 2,
    }
    cmds.objExists.return_value = True
    cmds.getAttr.side_effect = lambda attr: state[attr]
    cmds.setAttr.side_effect = lambda attr, value, **_kwargs: state.__setitem__(attr, value)

    result = load_and_call(
        "maya-render/scripts/set_render_settings.py",
        cmds,
        "main",
        renderer="arnold",
        width=1280,
        height=720,
        aa_samples=5,
    )

    assert result["success"] is True, result
    assert result["context"]["renderer"] == "arnold"
    assert result["context"]["width"] == 1280
    assert result["context"]["height"] == 720
    assert result["context"]["aa_samples"] == 5
    assert result["context"]["verified"] is True


def test_set_render_settings_round_trips_all_bounded_arnold_sampling_controls():
    cmds = MagicMock()
    state = {
        "defaultRenderGlobals.currentRenderer": "arnold",
        "defaultArnoldRenderOptions.AASamples": 2,
        "defaultArnoldRenderOptions.GIDiffuseSamples": 2,
        "defaultArnoldRenderOptions.GISpecularSamples": 2,
        "defaultArnoldRenderOptions.GITransmissionSamples": 2,
        "defaultArnoldRenderOptions.GISssSamples": 2,
        "defaultArnoldRenderOptions.GIVolumeSamples": 2,
    }
    cmds.objExists.return_value = True
    cmds.getAttr.side_effect = lambda attr: state[attr]
    cmds.setAttr.side_effect = lambda attr, value, **_kwargs: state.__setitem__(attr, value)

    result = load_and_call(
        "maya-render/scripts/set_render_settings.py",
        cmds,
        "main",
        aa_samples=4,
        diffuse_samples=3,
        specular_samples=3,
        transmission_samples=2,
        sss_samples=2,
        volume_samples=1,
    )

    assert result["success"] is True, result
    assert result["context"]["aa_samples"] == 4
    assert result["context"]["diffuse_samples"] == 3
    assert result["context"]["specular_samples"] == 3
    assert result["context"]["transmission_samples"] == 2
    assert result["context"]["sss_samples"] == 2
    assert result["context"]["volume_samples"] == 1
    assert result["context"]["verified"] is True


def test_set_render_settings_prevalidates_every_field_before_mutation():
    cmds = MagicMock()

    result = load_and_call(
        "maya-render/scripts/set_render_settings.py",
        cmds,
        "main",
        width=1280,
        aa_samples=99,
    )

    assert result["success"] is False
    assert "aa_samples" in result["error"]
    cmds.setAttr.assert_not_called()


def test_set_render_settings_rolls_back_previous_values_on_partial_failure():
    cmds = MagicMock()
    state = {
        "defaultResolution.width": 640,
        "defaultResolution.height": 360,
    }
    failed = {"height": False}
    cmds.getAttr.side_effect = lambda attr: state[attr]

    def _set_attr(attr, value, **_kwargs):
        if attr == "defaultResolution.height" and value == 720 and not failed["height"]:
            failed["height"] = True
            raise RuntimeError("locked height")
        state[attr] = value

    cmds.setAttr.side_effect = _set_attr

    result = load_and_call(
        "maya-render/scripts/set_render_settings.py",
        cmds,
        "main",
        width=1280,
        height=720,
    )

    assert result["success"] is False
    assert state == {
        "defaultResolution.width": 640,
        "defaultResolution.height": 360,
    }
