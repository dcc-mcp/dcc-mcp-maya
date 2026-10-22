"""Contract tests for the Maya texture baking skill."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from conftest import load_and_call


def test_bake_textures_defaults_to_arnold() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "dcc_mcp_maya"
        / "skills"
        / "maya-texture-bake"
        / "scripts"
        / "bake_textures.py"
    )
    namespace = {}
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
    assert inspect.signature(namespace["bake_textures"]).parameters["renderer"].default == "arnold"


def test_bake_textures_rejects_removed_mentalray() -> None:
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        object(),
        "main",
        objects=["mesh"],
        file_path="/tmp/bake",
        renderer="mentalRay",
    )
    assert result["success"] is False
    assert "Invalid renderer" in result["message"]


def _bake_cmds(tmp_path):
    cmds = MagicMock()
    cmds.objExists.return_value = True
    output = tmp_path / "baked.iff"
    state = {"renderer": "mayaSoftware", "selection": ["|previous"]}
    cmds.getAttr.side_effect = lambda attr: (
        state["renderer"] if attr == "defaultRenderGlobals.currentRenderer" else str(output)
    )
    cmds.setAttr.side_effect = lambda attr, value, **kw: state.update(renderer=value)
    cmds.ls.side_effect = lambda **kw: list(state["selection"])
    cmds.select.side_effect = lambda objects=None, **kw: state.update(selection=list(objects or []))

    def convert(*args, **kwargs):
        assert state["renderer"] == "arnold"
        output.write_bytes(b"baked texture")
        return ["bakedFile"]

    cmds.convertSolidTx.side_effect = convert
    return cmds, state, output


def test_bake_textures_activates_requested_renderer_before_conversion(tmp_path):
    cmds, state, output = _bake_cmds(tmp_path)
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )

    assert result["success"] is True, result
    assert result["context"]["baked_files"] == [str(output)]
    cmds.convertSolidTx.assert_called_once()


def test_bake_textures_schema_only_advertises_arnold() -> None:
    tools_path = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-texture-bake" / "tools.yaml"
    tools = yaml.safe_load(tools_path.read_text(encoding="utf-8"))["tools"]
    tool = next(item for item in tools if item["name"] == "bake_textures")
    assert tool["input_schema"]["properties"]["renderer"]["enum"] == ["arnold"]
    assert tool["input_schema"]["properties"]["renderer"]["default"] == "arnold"


def test_bake_textures_reports_failure_when_every_conversion_fails(tmp_path):
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.getAttr.return_value = "arnold"
    cmds.convertSolidTx.side_effect = RuntimeError("conversion failed")
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )
    assert result["success"] is False, result
    assert result["context"]["baked_count"] == 0
    assert result["context"]["failed_objects"] == [{"object": "mesh", "error": "conversion failed"}]
    assert result["context"]["partial"] is False


@pytest.mark.parametrize("conversion_error", [False, True])
def test_bake_textures_restores_renderer_and_selection(tmp_path, conversion_error):
    cmds, state, _ = _bake_cmds(tmp_path)
    if conversion_error:
        cmds.convertSolidTx.side_effect = RuntimeError("conversion failed")
    load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )
    assert state == {"renderer": "mayaSoftware", "selection": ["|previous"]}


@pytest.mark.parametrize("output_bytes", [None, b""])
def test_bake_textures_rejects_missing_or_empty_output(tmp_path, output_bytes):
    output = tmp_path / "baked.iff"
    if output_bytes is not None:
        output.write_bytes(output_bytes)
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.convertSolidTx.return_value = ["bakedFile"]
    cmds.getAttr.side_effect = lambda attr: str(output) if attr == "bakedFile.fileTextureName" else "arnold"
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )
    assert result["success"] is False, result
    assert result["context"]["baked_count"] == 0


def test_bake_textures_reports_partial_failure_with_verified_outputs(tmp_path):
    cmds, state, output = _bake_cmds(tmp_path)
    convert = cmds.convertSolidTx.side_effect

    def partial(obj, **kwargs):
        if obj == "broken":
            raise RuntimeError("cannot bake broken")
        return convert(obj, **kwargs)

    cmds.convertSolidTx.side_effect = partial
    prefix = str(tmp_path / "bake")
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh", "broken"],
        file_path=prefix,
    )
    assert result["success"] is False
    context = result["context"]
    assert context["partial"] is True
    assert context["baked_count"] == 1
    assert context["baked_objects"] == ["mesh"]
    assert context["baked_files"] == [str(output)]
    assert context["failed_objects"] == [{"object": "broken", "error": "cannot bake broken"}]
    assert context["file_path"] == prefix
    assert context["renderer"] == "arnold"
    assert state == {"renderer": "mayaSoftware", "selection": ["|previous"]}


def test_bake_textures_preserves_verified_files_when_another_output_is_missing(tmp_path):
    cmds, _, output = _bake_cmds(tmp_path)
    output.write_bytes(b"texture")
    cmds.convertSolidTx.side_effect = None
    cmds.convertSolidTx.return_value = ["bakedFile", "missingFile"]
    get_attr = cmds.getAttr.side_effect
    cmds.getAttr.side_effect = lambda attr: (
        str(tmp_path / "missing.iff") if attr == "missingFile.fileTextureName" else get_attr(attr)
    )
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )
    assert result["success"] is False
    assert result["context"]["baked_count"] == 0
    assert result["context"]["baked_files"] == [str(output)]
    assert result["context"]["partial"] is True


@pytest.mark.parametrize("returned_nodes", [None, [], "bakedFile"])
def test_bake_textures_validates_returned_file_nodes(tmp_path, returned_nodes):
    cmds, _, output = _bake_cmds(tmp_path)
    output.write_bytes(b"texture")
    cmds.convertSolidTx.side_effect = None
    cmds.convertSolidTx.return_value = returned_nodes
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )
    assert result["success"] is (returned_nodes == "bakedFile")


def test_bake_textures_resolves_project_relative_output_and_restores_empty_selection(tmp_path):
    cmds, state, output = _bake_cmds(tmp_path)
    state["selection"] = []
    get_attr = cmds.getAttr.side_effect
    cmds.getAttr.side_effect = lambda attr: (
        "textures/baked.iff" if attr == "bakedFile.fileTextureName" else get_attr(attr)
    )
    cmds.workspace.return_value = str(output)
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )
    assert result["success"] is True
    assert result["context"]["baked_files"] == [str(output)]
    assert state == {"renderer": "mayaSoftware", "selection": []}


@pytest.mark.parametrize("failure_stage", ["activation", "selection", "renderer_restore"])
def test_bake_textures_restores_state_after_setup_or_cleanup_failure(tmp_path, failure_stage):
    cmds, state, _ = _bake_cmds(tmp_path)
    set_attr = cmds.setAttr.side_effect
    select = cmds.select.side_effect

    def set_renderer(attr, value, **kwargs):
        if failure_stage == "renderer_restore" and value == "mayaSoftware":
            raise RuntimeError("cannot restore renderer")
        set_attr(attr, value, **kwargs)
        if failure_stage == "activation" and value == "arnold":
            raise RuntimeError("activation failed after mutation")

    def select_objects(objects=None, **kwargs):
        select(objects, **kwargs)
        if failure_stage == "selection" and objects == ["mesh"]:
            raise RuntimeError("selection failed after mutation")

    cmds.setAttr.side_effect = set_renderer
    cmds.select.side_effect = select_objects
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        cmds,
        "main",
        objects=["mesh"],
        file_path=str(tmp_path / "bake"),
    )
    assert result["success"] is False
    assert state["selection"] == ["|previous"]
    assert state["renderer"] == ("arnold" if failure_stage == "renderer_restore" else "mayaSoftware")
