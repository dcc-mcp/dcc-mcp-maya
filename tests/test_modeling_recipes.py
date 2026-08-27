"""Production-contract tests for the bundled Maya modeling recipe pack."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from conftest import load_and_call
from dcc_mcp_core import scan_and_load_strict, yaml_loads
from dcc_mcp_core.recipes import register_recipes_tools
from jsonschema import Draft202012Validator, ValidationError

SKILLS_ROOT = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills"
EXPECTED_RECIPES = {
    "auto_uv_for_export",
    "loft_hull_from_sections",
    "mirror_assembly",
    "radial_array",
}


def _recipe_handlers():
    loaded, skipped = scan_and_load_strict(extra_paths=[str(SKILLS_ROOT)], dcc_name="maya")
    assert skipped == []

    server = MagicMock()
    handlers = {}
    server.register_handler.side_effect = lambda name, handler: handlers.__setitem__(name, handler)
    register_recipes_tools(server, skills=loaded, dcc_name="maya")
    return handlers


def _materialize_arguments(arguments, inputs):
    materialized = {}
    for name, value in arguments.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            materialized[name] = inputs[value[2:-1]]
        else:
            materialized[name] = value
    return materialized


def _execute_typed_test_step(step, inputs, cmds):
    """Compose a real application-plan step with its published tool and script contracts.

    Core deliberately returns a plan rather than executing it. This helper is test-only:
    it validates the materialized arguments against the registered schema, then invokes
    the actual bundled skill entry point with Maya mocked only at the licensed-host edge.
    """
    skill_slug, action = step["tool"].split("__", 1)
    skill_name = skill_slug.replace("_", "-")
    manifest = yaml_loads((SKILLS_ROOT / skill_name / "tools.yaml").read_text(encoding="utf-8"))
    contract = next(item for item in manifest["tools"] if item["name"] == action)
    arguments = _materialize_arguments(step["arguments"], inputs)
    Draft202012Validator(contract["input_schema"]).validate(arguments)
    return load_and_call(
        "{}/scripts/{}.py".format(skill_name, action),
        cmds,
        "main",
        **arguments,
    )


def test_loft_recipe_is_discoverable_and_materializes_typed_step_plan():
    handlers = _recipe_handlers()

    search = handlers["recipes__search"](json.dumps({"query": "loft", "dcc": "maya"}))
    assert search["success"] is True
    assert [recipe["name"] for recipe in search["context"]["recipes"]] == ["loft_hull_from_sections"]

    applied = handlers["recipes__apply"](
        json.dumps(
            {
                "skill": "maya-mesh-ops",
                "recipe": "loft_hull_from_sections",
                "inputs": {
                    "sections": ["hull_section_front", "hull_section_mid", "hull_section_rear"],
                    "name": "attack_hull",
                },
            },
        ),
    )
    assert applied["success"] is True
    assert applied["context"]["inputs"] == {
        "sections": ["hull_section_front", "hull_section_mid", "hull_section_rear"],
        "name": "attack_hull",
    }
    assert applied["context"]["steps"] == [
        {
            "tool": "maya_mesh_ops__loft_sections",
            "arguments": {
                "sections": "${sections}",
                "name": "${name}",
            },
        },
    ]


def test_modeling_recipe_catalog_routes_only_to_published_typed_tools():
    handlers = _recipe_handlers()

    listed = handlers["recipes__list"](json.dumps({"skill": "maya-mesh-ops"}))
    assert listed["success"] is True
    recipes = listed["context"]["recipes"]
    assert {recipe["name"] for recipe in recipes} == EXPECTED_RECIPES

    published_tools = set()
    for tool_file in SKILLS_ROOT.glob("*/tools.yaml"):
        manifest = yaml_loads(tool_file.read_text(encoding="utf-8"))
        skill_slug = tool_file.parent.name.replace("-", "_")
        published_tools.update("{}__{}".format(skill_slug, tool["name"]) for tool in manifest.get("tools", []))

    routed_tools = {step["tool"] for recipe in recipes for step in recipe["steps"]}
    assert routed_tools <= published_tools
    assert "maya_mesh_ops__loft_sections" in routed_tools
    assert "maya_mesh_ops__mirror_mesh" in routed_tools
    assert "maya_mesh_ops__array_instances" in routed_tools
    assert "maya_uv_ops__auto_uv" in routed_tools


def test_auto_uv_recipe_requires_deterministic_inputs_and_redacts_invalid_values():
    handlers = _recipe_handlers()

    incomplete = handlers["recipes__apply"](
        json.dumps(
            {
                "skill": "maya-mesh-ops",
                "recipe": "auto_uv_for_export",
                "inputs": {"object_name": "export_body"},
            },
        ),
    )
    assert incomplete["success"] is False
    assert incomplete["context"]["errors"] == [
        "Missing required input: planes",
        "Missing required input: percentage_space",
    ]

    sensitive_value = "do-not-echo-this-value"
    invalid = handlers["recipes__apply"](
        json.dumps(
            {
                "skill": "maya-mesh-ops",
                "recipe": "auto_uv_for_export",
                "inputs": {
                    "object_name": "export_body",
                    "planes": sensitive_value,
                    "percentage_space": 0.2,
                },
            },
        ),
    )
    assert invalid["success"] is False
    assert invalid["message"] == "Recipe inputs are invalid."
    assert invalid["context"]["errors"] == ["Input 'planes' expected integer, got str"]
    assert sensitive_value not in json.dumps(invalid)


def test_mirror_assembly_publishes_only_the_safe_in_place_mirror_contract():
    handlers = _recipe_handlers()

    applied = handlers["recipes__apply"](
        json.dumps(
            {
                "skill": "maya-mesh-ops",
                "recipe": "mirror_assembly",
                "inputs": {
                    "object_name": "pylon_assembly",
                    "axis": "x",
                },
            },
        ),
    )
    assert applied["success"] is True
    assert applied["context"]["steps"] == [
        {
            "tool": "maya_mesh_ops__mirror_mesh",
            "arguments": {"object_name": "${object_name}", "axis": "${axis}"},
        },
    ]

    listed = handlers["recipes__list"](json.dumps({"skill": "maya-mesh-ops"}))
    recipe = next(item for item in listed["context"]["recipes"] if item["name"] == "mirror_assembly")
    assert recipe["inputs_schema"]["required"] == ["object_name", "axis"]
    assert "does not create or preserve a separate original" in recipe["description"].lower()


def test_mirror_recipe_output_is_the_registered_final_tool_receipt():
    handlers = _recipe_handlers()
    listed = handlers["recipes__list"](json.dumps({"skill": "maya-mesh-ops"}))
    recipe = next(item for item in listed["context"]["recipes"] if item["name"] == "mirror_assembly")

    manifest = yaml_loads((SKILLS_ROOT / "maya-mesh-ops" / "tools.yaml").read_text(encoding="utf-8"))
    mirror_tool = next(item for item in manifest["tools"] if item["name"] == "mirror_mesh")

    assert recipe["output_contract"] == mirror_tool["output_schema"]


def test_mirror_recipe_executes_in_place_and_rejects_legacy_name_dataflow():
    handlers = _recipe_handlers()
    legacy = handlers["recipes__apply"](
        json.dumps(
            {
                "skill": "maya-mesh-ops",
                "recipe": "mirror_assembly",
                "inputs": {
                    "objects": ["only_one_part"],
                    "combined_name": "assembly",
                    "mirrored_name": "already_taken",
                    "axis": "x",
                },
            },
        ),
    )
    assert legacy["success"] is False
    assert "only_one_part" not in json.dumps(legacy)
    assert "already_taken" not in json.dumps(legacy)

    inputs = {"object_name": "assembly", "axis": "x"}
    applied = handlers["recipes__apply"](
        json.dumps({"skill": "maya-mesh-ops", "recipe": "mirror_assembly", "inputs": inputs}),
    )
    assert applied["success"] is True

    cmds = MagicMock()
    cmds.objExists.side_effect = lambda name: name in {"assembly", "already_taken"}
    cmds.polyEvaluate.side_effect = [12, 24]
    result = _execute_typed_test_step(applied["context"]["steps"][0], inputs, cmds)

    assert result["success"] is True, result
    assert result["context"]["object_name"] == "assembly"
    assert result["context"]["faces_before"] == 12
    assert result["context"]["faces_after"] == 24
    Draft202012Validator(applied["context"]["output_contract"]).validate(result["context"])
    cmds.polyUnite.assert_not_called()
    cmds.rename.assert_not_called()


def test_radial_array_executes_verified_world_pivot_before_bounded_instances():
    handlers = _recipe_handlers()
    inputs = {
        "object_name": "rotor_blade",
        "count": 3,
        "pivot": [1.0, 2.0, 3.0],
        "rotate_step": [0.0, 120.0, 0.0],
        "name_prefix": "rotor_blade",
    }
    applied = handlers["recipes__apply"](
        json.dumps({"skill": "maya-mesh-ops", "recipe": "radial_array", "inputs": inputs}),
    )
    assert applied["success"] is True
    assert [step["tool"] for step in applied["context"]["steps"]] == [
        "maya_mesh_ops__set_pivot",
        "maya_mesh_ops__array_instances",
    ]

    pivot_cmds = MagicMock()
    pivot_cmds.objExists.return_value = True
    pivot_cmds.undoInfo.return_value = True
    pivot_cmds.xform.side_effect = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        None,
        [1.0, 2.0, 3.0, 1.0, 2.0, 3.0],
    ]
    pivot_result = _execute_typed_test_step(applied["context"]["steps"][0], inputs, pivot_cmds)
    assert pivot_result["success"] is True, pivot_result
    assert pivot_result["context"]["rotate_pivot"] == inputs["pivot"]
    assert pivot_result["context"]["scale_pivot"] == inputs["pivot"]

    array_cmds = MagicMock()
    array_cmds.objExists.return_value = True
    array_cmds.undoInfo.return_value = True
    array_cmds.instance.side_effect = [["rotor_blade_01"], ["rotor_blade_02"]]
    array_cmds.listRelatives.return_value = ["rotor_bladeShape"]
    uuid_by_node = {
        "rotor_blade": "transform-source",
        "rotor_bladeShape": "shape-source",
        "rotor_blade_01": "transform-01",
        "rotor_blade_02": "transform-02",
    }

    def _ls(*args, **kwargs):
        if not kwargs.get("uuid"):
            return list(args)
        if args:
            return [uuid_by_node[str(args[0])]]
        return ["transform-source", "shape-source"]

    rotations = {
        "rotor_blade": [0.0, 0.0, 0.0],
        "rotor_blade_01": [0.0, 120.0, 0.0],
        "rotor_blade_02": [0.0, 240.0, 0.0],
    }

    def _xform(node, **kwargs):
        if kwargs.get("query") and kwargs.get("translation"):
            return [0.0, 0.0, 0.0]
        if kwargs.get("query") and kwargs.get("rotation"):
            return rotations[node]
        return None

    array_cmds.ls.side_effect = _ls
    array_cmds.xform.side_effect = _xform
    array_result = _execute_typed_test_step(applied["context"]["steps"][1], inputs, array_cmds)

    assert array_result["success"] is True, array_result
    assert array_result["context"]["verified_count"] == 3
    assert array_result["context"]["rotate_step"] == inputs["rotate_step"]
    Draft202012Validator(applied["context"]["output_contract"]).validate(array_result["context"])


def test_published_schemas_are_valid_and_uv_contract_fails_without_verified_uvs():
    handlers = _recipe_handlers()
    listed = handlers["recipes__list"](json.dumps({"skill": "maya-mesh-ops"}))
    recipes = {recipe["name"]: recipe for recipe in listed["context"]["recipes"]}

    for recipe in recipes.values():
        Draft202012Validator.check_schema(recipe["inputs_schema"])
        Draft202012Validator.check_schema(recipe["output_contract"])

    uv_contract = Draft202012Validator(recipes["auto_uv_for_export"]["output_contract"])
    valid_result = {
        "object_name": "export_body",
        "uv_set": "map1",
        "uv_count": 128,
        "uv_digest": "a" * 64,
        "changed": True,
        "planes": 6,
    }
    uv_contract.validate(valid_result)

    with pytest.raises(ValidationError):
        uv_contract.validate({**valid_result, "uv_count": 0})
    with pytest.raises(ValidationError):
        uv_contract.validate({key: value for key, value in valid_result.items() if key != "uv_count"})
