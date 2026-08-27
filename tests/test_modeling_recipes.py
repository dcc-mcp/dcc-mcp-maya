"""Production-contract tests for the bundled Maya modeling recipe pack."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
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


def test_mirror_assembly_combines_named_parts_before_mirroring_and_renaming():
    handlers = _recipe_handlers()

    applied = handlers["recipes__apply"](
        json.dumps(
            {
                "skill": "maya-mesh-ops",
                "recipe": "mirror_assembly",
                "inputs": {
                    "objects": ["left_pylon", "left_mount"],
                    "combined_name": "left_pylon_assembly",
                    "mirrored_name": "right_pylon_assembly",
                    "axis": "x",
                },
            },
        ),
    )
    assert applied["success"] is True
    assert [step["tool"] for step in applied["context"]["steps"]] == [
        "maya_mesh_ops__combine_meshes",
        "maya_mesh_ops__mirror_mesh",
        "maya_primitives__rename_object",
    ]
    assert applied["context"]["steps"][0]["arguments"] == {
        "objects": "${objects}",
        "name": "${combined_name}",
    }


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
