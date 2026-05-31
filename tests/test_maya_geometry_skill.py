"""Unit tests for the maya-geometry skill (Interchange stage)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from pathlib import Path
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call, load_and_call_with_mel


def test_file_exists_uses_filesystem(tmp_path):
    path = tmp_path / "mesh.fbx"
    path.write_text("x")
    cmds = MagicMock()

    result = load_and_call("maya-geometry/scripts/file_exists.py", cmds, "main", path=str(path))

    assert result["success"] is True
    assert result["context"]["exists"] is True


def test_import_file_loads_required_plugin_before_import(tmp_path):
    path = tmp_path / "cache.abc"
    path.write_bytes(b"abc")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    cmds.ls.return_value = ["cacheRoot"]

    result = load_and_call("maya-geometry/scripts/import_file.py", cmds, "main", file_path=str(path))

    assert result["success"] is True, result
    cmds.pluginInfo.assert_called_once_with("AbcImport", query=True, loaded=True)
    cmds.loadPlugin.assert_called_once_with("AbcImport")
    args, kwargs = cmds.file.call_args
    assert args[0] == str(path).replace("\\", "/")
    assert kwargs["i"] is True
    assert result["context"]["loaded_plugins"] == ["AbcImport"]


def test_import_file_disables_maya_import_prompts(tmp_path):
    path = tmp_path / "scene.ma"
    path.write_text("// maya ascii")
    cmds = MagicMock()
    cmds.ls.return_value = ["pCube1"]

    result = load_and_call("maya-geometry/scripts/import_file.py", cmds, "main", file_path=str(path))

    assert result["success"] is True, result
    _args, kwargs = cmds.file.call_args
    assert kwargs["i"] is True
    assert kwargs["prompt"] is False


def test_import_file_skips_plugin_load_for_native_maya_file(tmp_path):
    path = tmp_path / "scene.ma"
    path.write_text("// maya ascii")
    cmds = MagicMock()
    cmds.ls.return_value = []

    result = load_and_call("maya-geometry/scripts/import_file.py", cmds, "main", file_path=str(path))

    assert result["success"] is True, result
    cmds.pluginInfo.assert_not_called()
    cmds.loadPlugin.assert_not_called()


def test_export_fbx_pushes_options_through_mel_and_verifies(tmp_path):
    """The MEL-driven rewrite pushes every FBXExport* option through
    ``mel.eval`` before invoking ``cmds.file``, then verifies the
    destination has non-zero size.
    """
    cmds = MagicMock()
    mel = MagicMock()
    cmds.pluginInfo.return_value = False
    out_path = tmp_path / "out.fbx"

    def _write_file(path, **_kwargs):
        out_path.write_bytes(b"FBX-bytes")
        return str(out_path)

    cmds.file.side_effect = _write_file

    result = load_and_call_with_mel(
        "maya-geometry/scripts/export_fbx.py",
        cmds,
        mel,
        "main",
        path=str(out_path),
        selected_only=True,
        bake_animation=True,
        start_frame=1,
        end_frame=10,
        fbx_version="FBX202000",
        up_axis="y",
    )

    assert result["success"] is True, result
    ctx = result["context"]
    assert ctx["selected_only"] is True
    assert ctx["size_bytes"] == len(b"FBX-bytes")
    applied = ctx["applied_options"]
    # Every meaningful option lands in the applied bag.
    assert applied["FBXExportBakeComplexAnimation"] == "true"
    assert applied["FBXExportBakeComplexStart"] == 1
    assert applied["FBXExportBakeComplexEnd"] == 10
    assert applied["FBXExportFileVersion"] == "FBX202000"
    assert applied["FBXExportUpAxis"] == "y"
    # Plugin loaded; options reset before configuration; cmds.file selected-only.
    cmds.pluginInfo.assert_called_with("fbxmaya", query=True, loaded=True)
    cmds.loadPlugin.assert_called_once_with("fbxmaya")
    mel.eval.assert_any_call("FBXResetExport")
    cmds.file.assert_called_once()
    file_args, file_kwargs = cmds.file.call_args
    assert file_args[0] == str(out_path).replace("\\", "/")
    assert file_kwargs.get("type") == "FBX export"
    assert file_kwargs.get("exportSelected") is True


def test_export_fbx_reports_zero_byte_failure(tmp_path):
    """A 0-byte FBX file must fail explicitly so the agent does not
    proceed with a corrupt round-trip."""
    cmds = MagicMock()
    mel = MagicMock()
    cmds.pluginInfo.return_value = True
    out_path = tmp_path / "empty.fbx"

    def _write_empty(path, **_kwargs):
        out_path.write_bytes(b"")
        return str(out_path)

    cmds.file.side_effect = _write_empty

    result = load_and_call_with_mel(
        "maya-geometry/scripts/export_fbx.py",
        cmds,
        mel,
        "main",
        path=str(out_path),
    )

    assert result["success"] is False
    assert "0-byte" in result["message"]
    assert result["context"]["path"].endswith("empty.fbx")


def test_export_fbx_rejects_unknown_fbx_version(tmp_path):
    cmds = MagicMock()
    mel = MagicMock()
    cmds.pluginInfo.return_value = True

    result = load_and_call_with_mel(
        "maya-geometry/scripts/export_fbx.py",
        cmds,
        mel,
        "main",
        path=str(tmp_path / "out.fbx"),
        fbx_version="FBX9999",
    )

    assert result["success"] is False
    # cmds.file must not be reached when the parameter validation fails.
    cmds.file.assert_not_called()


def test_import_fbx_returns_new_node_names(tmp_path):
    fbx_path = tmp_path / "in.fbx"
    fbx_path.write_bytes(b"FBX-bytes")
    cmds = MagicMock()
    mel = MagicMock()
    cmds.pluginInfo.return_value = True

    # Simulate cmds.ls before/after the import.
    before_nodes = ["|persp", "|top", "|front", "|side"]
    after_nodes = before_nodes + ["|imported_grp", "|imported_grp|mesh1"]
    cmds.ls.side_effect = [before_nodes, after_nodes]
    cmds.objectType.return_value = "transform"

    result = load_and_call_with_mel(
        "maya-geometry/scripts/import_fbx.py",
        cmds,
        mel,
        "main",
        path=str(fbx_path),
        namespace="ns",
    )

    assert result["success"] is True, result
    ctx = result["context"]
    assert "imported_grp" in ctx["imported_short_names"]
    assert "mesh1" in ctx["imported_short_names"]
    assert ctx["namespace"] == "ns"
    cmds.loadPlugin.assert_not_called()  # plugin already loaded
    cmds.file.assert_called_once()


def test_import_fbx_disables_maya_import_prompts(tmp_path):
    fbx_path = tmp_path / "in.fbx"
    fbx_path.write_bytes(b"FBX-bytes")
    cmds = MagicMock()
    mel = MagicMock()
    cmds.pluginInfo.return_value = True
    cmds.ls.side_effect = [[], ["|imported_grp"]]
    cmds.objectType.return_value = "transform"

    result = load_and_call_with_mel(
        "maya-geometry/scripts/import_fbx.py",
        cmds,
        mel,
        "main",
        path=str(fbx_path),
    )

    assert result["success"] is True, result
    _args, kwargs = cmds.file.call_args
    assert kwargs["i"] is True
    assert kwargs["prompt"] is False


def test_import_fbx_rejects_missing_path(tmp_path):
    cmds = MagicMock()
    mel = MagicMock()
    cmds.pluginInfo.return_value = True

    result = load_and_call_with_mel(
        "maya-geometry/scripts/import_fbx.py",
        cmds,
        mel,
        "main",
        path=str(tmp_path / "nonexistent.fbx"),
    )

    assert result["success"] is False
    assert "not found" in result["message"].lower() or "missing" in result["message"].lower()


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


def test_export_alembic_loads_plugin_and_verifies_output(tmp_path):
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    cmds.ls.return_value = ["pCube1"]
    out_path = tmp_path / "out.abc"

    def _write_abc(j):
        out_path.write_bytes(b"ABC-bytes")

    cmds.AbcExport.side_effect = _write_abc

    result = load_and_call(
        "maya-geometry/scripts/export_alembic.py",
        cmds,
        "main",
        file_path=str(out_path),
    )

    assert result["success"] is True, result
    assert result["context"]["size_bytes"] == len(b"ABC-bytes")
    cmds.pluginInfo.assert_called_once_with("AbcExport", query=True, loaded=True)
    cmds.loadPlugin.assert_called_once_with("AbcExport")
    cmds.AbcExport.assert_called_once()
    job = cmds.AbcExport.call_args[1]["j"]
    assert "-root pCube1" in job
    assert '-file "{}"'.format(str(out_path).replace("\\", "/")) in job


def test_geometry_tools_yaml_declares_affinity():
    tools_yaml = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-geometry" / "tools.yaml"
    text = tools_yaml.read_text(encoding="utf-8")

    assert "name: file_exists" in text
    assert "affinity: any" in text
    assert "name: create_sphere" not in text
    assert text.count("affinity: main") >= 3
    # Interchange skill must expose both export and import contracts.
    assert "name: export_fbx" in text
    assert "name: export_alembic" in text
    assert "name: import_fbx" in text
