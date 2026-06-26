"""Unit tests for maya-materials skill scripts."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def test_set_material_attribute_maps_arnold_metallic_to_metalness():
    cmds = MagicMock()
    cmds.objExists.side_effect = lambda plug: plug in {"carPaint", "carPaint.metalness"}
    cmds.nodeType.return_value = "aiStandardSurface"

    def _plugin_info(_plugin, **kwargs):
        if kwargs.get("loaded"):
            return True
        if kwargs.get("version"):
            return "5.0.0.3"
        return None

    cmds.pluginInfo.side_effect = _plugin_info

    result = load_and_call(
        "maya-materials/scripts/set_material_attribute.py",
        cmds,
        "main",
        material_name="carPaint",
        attribute="metallic",
        value=0.7,
    )

    assert result["success"] is True, result
    assert result["context"]["requested_attribute"] == "metallic"
    assert result["context"]["attribute"] == "metalness"
    assert result["context"]["attribute_alias_applied"] is True
    assert result["context"]["mtoa_version"] == "5.0.0.3"
    cmds.setAttr.assert_called_once_with("carPaint.metalness", 0.7)


def test_set_material_attribute_keeps_existing_attribute():
    cmds = MagicMock()
    cmds.objExists.side_effect = lambda plug: plug in {"lambert1", "lambert1.color"}
    cmds.nodeType.return_value = "lambert"

    result = load_and_call(
        "maya-materials/scripts/set_material_attribute.py",
        cmds,
        "main",
        material_name="lambert1",
        attribute="color",
        value=[1.0, 0.0, 0.0],
    )

    assert result["success"] is True, result
    assert result["context"]["attribute"] == "color"
    assert result["context"]["attribute_alias_applied"] is False
    cmds.setAttr.assert_called_once_with("lambert1.color", 1.0, 0.0, 0.0, type="double3")
