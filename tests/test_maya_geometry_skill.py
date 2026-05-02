"""Unit tests for the maya-geometry skill."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from pathlib import Path
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call


def test_create_sphere_calls_poly_sphere():
    cmds = MagicMock()
    cmds.polySphere.return_value = ["heroSphere", "heroSphereShape"]

    result = load_and_call(
        "maya-geometry/scripts/create_sphere.py",
        cmds,
        "main",
        radius=2.5,
        name="heroSphere",
    )

    assert result["success"] is True
    assert result["context"]["object_name"] == "heroSphere"
    cmds.polySphere.assert_called_once_with(radius=2.5, name="heroSphere")


def test_create_sphere_rejects_invalid_radius():
    cmds = MagicMock()

    result = load_and_call("maya-geometry/scripts/create_sphere.py", cmds, "main", radius=0)

    assert result["success"] is False
    cmds.polySphere.assert_not_called()


def test_save_scene_renames_and_saves():
    cmds = MagicMock()
    cmds.file.side_effect = [None, "c:/tmp/test.ma"]

    result = load_and_call(
        "maya-geometry/scripts/save_scene.py",
        cmds,
        "main",
        path="c:/tmp/test.ma",
        file_type="mayaAscii",
    )

    assert result["success"] is True
    cmds.file.assert_any_call(rename="c:/tmp/test.ma")
    cmds.file.assert_any_call(save=True, type="mayaAscii")


def test_file_exists_uses_filesystem(tmp_path):
    path = tmp_path / "mesh.fbx"
    path.write_text("x")
    cmds = MagicMock()

    result = load_and_call("maya-geometry/scripts/file_exists.py", cmds, "main", path=str(path))

    assert result["success"] is True
    assert result["context"]["exists"] is True


def test_export_fbx_loads_plugin_and_exports_selection():
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    cmds.file.return_value = "c:/tmp/out.fbx"

    result = load_and_call(
        "maya-geometry/scripts/export_fbx.py",
        cmds,
        "main",
        path="c:/tmp/out.fbx",
        selected_only=True,
    )

    assert result["success"] is True
    cmds.pluginInfo.assert_called_once_with("fbxmaya", query=True, loaded=True)
    cmds.loadPlugin.assert_called_once_with("fbxmaya")
    cmds.file.assert_called_once_with(
        "c:/tmp/out.fbx",
        force=True,
        options="v=0;",
        type="FBX export",
        exportSelected=True,
    )


def test_export_obj_loads_plugin_and_exports_all():
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    cmds.file.return_value = "c:/tmp/out.obj"

    result = load_and_call("maya-geometry/scripts/export_obj.py", cmds, "main", path="c:/tmp/out.obj")

    assert result["success"] is True
    cmds.pluginInfo.assert_called_once_with("objExport", query=True, loaded=True)
    cmds.loadPlugin.assert_called_once_with("objExport")
    _args, kwargs = cmds.file.call_args
    assert kwargs["type"] == "OBJexport"
    assert kwargs["exportAll"] is True


def test_geometry_tools_yaml_declares_affinity():
    tools_yaml = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-geometry" / "tools.yaml"
    text = tools_yaml.read_text(encoding="utf-8")

    assert "name: file_exists" in text
    assert "affinity: any" in text
    assert text.count("affinity: main") >= 4
