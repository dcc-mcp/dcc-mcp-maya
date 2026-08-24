"""Public-contract tests for the typed Maya polygon-modeling vocabulary."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import yaml
from conftest import load_and_call

SKILL_ROOT = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-mesh-ops"


def test_loft_sections_is_discoverable_and_verifies_a_polygon_mesh():
    """The first modeling delta must be typed and prove its Maya result."""
    tools = yaml.safe_load((SKILL_ROOT / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    contract = next(item for item in tools if item["name"] == "loft_sections")

    assert contract["execution"] == "sync"
    assert contract["affinity"] == "main"
    assert contract["group"] == "modeling"
    assert contract["input_schema"]["additionalProperties"] is False
    assert contract["input_schema"]["properties"]["sections"]["maxItems"] == 64

    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.objectType.side_effect = lambda node: "nurbsCurve" if node in {"sectionAShape", "sectionBShape"} else "mesh"
    cmds.listRelatives.side_effect = lambda node, **kwargs: ["{}Shape".format(node)] if kwargs.get("shapes") else None
    cmds.loft.return_value = ["loftedMesh", "loft1"]
    cmds.rename.return_value = "bodyLoft"
    cmds.undoInfo.return_value = True
    cmds.listHistory.return_value = ["loft1"]
    cmds.listConnections.return_value = ["sectionAShape", "sectionBShape"]
    uuid_by_node = {
        "sectionAShape": "section-a-shape",
        "sectionBShape": "section-b-shape",
        "bodyLoft": "loft-transform-new",
        "bodyLoftShape": "loft-shape-new",
        "loft1": "loft-history-new",
    }

    def _loft_ls(*args, **kwargs):
        if not kwargs.get("uuid"):
            return list(args)
        if args:
            return [uuid_by_node[str(args[0])]]
        return ["section-a-shape", "section-b-shape"]

    cmds.ls.side_effect = _loft_ls

    result = load_and_call(
        "maya-mesh-ops/scripts/loft_sections.py",
        cmds,
        "main",
        sections=["sectionA", "sectionB"],
        name="bodyLoft",
        degree=3,
        close=False,
    )

    assert result["success"] is True, result
    assert result["context"]["object_name"] == "bodyLoft"
    assert result["context"]["shape"] == "bodyLoftShape"
    assert result["context"]["input_sections"] == ["sectionA", "sectionB"]
    cmds.loft.assert_called_once()
    assert cmds.loft.call_args[0] == ("sectionA", "sectionB")
    assert cmds.loft.call_args[1]["polygon"] == 1
    cmds.rename.assert_called_once_with("loftedMesh", "bodyLoft")


def test_modeling_contract_exposes_only_bounded_typed_deltas():
    tools = yaml.safe_load((SKILL_ROOT / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    by_name = {item["name"]: item for item in tools}

    for name in ("loft_sections", "lathe_profile", "array_instances", "set_pivot"):
        contract = by_name[name]
        assert contract["execution"] == "sync"
        assert contract["affinity"] == "main"
        assert contract["group"] == "modeling"
        assert contract["input_schema"]["additionalProperties"] is False
        assert contract["output_schema"]["type"] == "object"

    assert by_name["array_instances"]["input_schema"]["properties"]["count"]["maximum"] == 128
    groups = yaml.safe_load((SKILL_ROOT / "groups.yaml").read_text(encoding="utf-8"))["groups"]
    modeling = next(group for group in groups if group["name"] == "modeling")
    assert modeling["default_active"] is False
    assert {"loft_sections", "lathe_profile", "array_instances", "set_pivot"} <= set(modeling["tools"])


def test_lathe_profile_verifies_the_polygon_result():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.objectType.side_effect = lambda node: "nurbsCurve" if node == "profileShape" else "mesh"
    cmds.listRelatives.side_effect = lambda node, **kwargs: (
        ["profileShape"] if node == "profile" else ["lathedBodyShape"]
    )
    cmds.revolve.return_value = ["revolvedSurface", "revolve1"]
    cmds.rename.return_value = "lathedBody"
    cmds.undoInfo.return_value = True
    cmds.listHistory.return_value = ["revolve1"]
    cmds.listConnections.return_value = ["profileShape"]
    uuid_by_node = {
        "profileShape": "profile-shape",
        "lathedBody": "lathe-transform-new",
        "lathedBodyShape": "lathe-shape-new",
        "revolve1": "lathe-history-new",
    }

    def _lathe_ls(*args, **kwargs):
        if not kwargs.get("uuid"):
            return list(args)
        if args:
            return [uuid_by_node[str(args[0])]]
        return ["profile-shape"]

    cmds.ls.side_effect = _lathe_ls

    result = load_and_call(
        "maya-mesh-ops/scripts/lathe_profile.py",
        cmds,
        "main",
        profile="profile",
        name="lathedBody",
        axis="y",
        segments=24,
        sweep_angle=360.0,
    )

    assert result["success"] is True, result
    assert result["context"]["object_name"] == "lathedBody"
    assert result["context"]["shape"] == "lathedBodyShape"
    assert result["context"]["axis"] == "y"
    assert cmds.revolve.call_args[1]["polygon"] == 1
    assert cmds.revolve.call_args[1]["endSweep"] == 360.0
    assert "sweep" not in cmds.revolve.call_args[1]


def test_array_instances_reads_back_every_requested_transform():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.instance.side_effect = [["rotorBlade_01"], ["rotorBlade_02"], ["rotorBlade_03"]]
    cmds.undoInfo.return_value = True
    cmds.listRelatives.side_effect = lambda node, **_kwargs: ["{}Shape".format(node)]
    uuid_by_node = {
        "rotorBlade": "transform-source",
        "rotorBladeShape": "shape-source",
        "rotorBlade_01": "transform-01",
        "rotorBlade_01Shape": "shape-source",
        "rotorBlade_02": "transform-02",
        "rotorBlade_02Shape": "shape-source",
        "rotorBlade_03": "transform-03",
        "rotorBlade_03Shape": "shape-source",
    }

    def _array_ls(*args, **kwargs):
        if not kwargs.get("uuid"):
            return list(args)
        if args:
            return [uuid_by_node[str(args[0])]]
        return ["transform-source", "shape-source"]

    cmds.ls.side_effect = _array_ls
    translations = {
        "rotorBlade": [0.0, 0.0, 0.0],
        "rotorBlade_01": [2.0, 0.0, 0.0],
        "rotorBlade_02": [4.0, 0.0, 0.0],
        "rotorBlade_03": [6.0, 0.0, 0.0],
    }
    rotations = {
        "rotorBlade": [0.0, 0.0, 0.0],
        "rotorBlade_01": [0.0, 90.0, 0.0],
        "rotorBlade_02": [0.0, 180.0, 0.0],
        "rotorBlade_03": [0.0, 270.0, 0.0],
    }

    def _xform(node, **kwargs):
        if kwargs.get("query") and kwargs.get("translation"):
            return translations[node]
        if kwargs.get("query") and kwargs.get("rotation"):
            return rotations[node]
        return None

    cmds.xform.side_effect = _xform

    result = load_and_call(
        "maya-mesh-ops/scripts/array_instances.py",
        cmds,
        "main",
        object_name="rotorBlade",
        count=4,
        translate_step=[2.0, 0.0, 0.0],
        rotate_step=[0.0, 90.0, 0.0],
        name_prefix="rotorBlade",
    )

    assert result["success"] is True, result
    assert result["context"]["objects"] == [
        "rotorBlade",
        "rotorBlade_01",
        "rotorBlade_02",
        "rotorBlade_03",
    ]
    assert result["context"]["verified_count"] == 4
    assert cmds.instance.call_count == 3


def test_array_instances_rejects_unbounded_counts_before_maya_mutation():
    cmds = MagicMock()

    result = load_and_call(
        "maya-mesh-ops/scripts/array_instances.py",
        cmds,
        "main",
        object_name="blade",
        count=129,
    )

    assert result["success"] is False
    cmds.instance.assert_not_called()


def test_array_instances_rejects_source_name_replay_and_rolls_back():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.undoInfo.return_value = True
    cmds.instance.return_value = ["blade"]
    cmds.xform.return_value = [0.0, 0.0, 0.0]
    cmds.listRelatives.return_value = ["bladeShape"]
    uuid_by_node = {"blade": "transform-source", "bladeShape": "shape-source"}
    inventory_calls = 0

    def _ls(*args, **kwargs):
        nonlocal inventory_calls
        if not kwargs.get("uuid"):
            return list(args)
        if args:
            return [uuid_by_node[str(args[0])]]
        inventory_calls += 1
        return ["transform-source", "shape-source"]

    cmds.ls.side_effect = _ls

    result = load_and_call(
        "maya-mesh-ops/scripts/array_instances.py",
        cmds,
        "main",
        object_name="blade",
        count=2,
    )

    assert result["success"] is False
    assert result["context"]["rollback_attempted"] is True
    assert result["context"]["rollback_verified"] is True
    assert inventory_calls >= 2
    cmds.undo.assert_called_once_with()


def test_loft_sections_rejects_preexisting_mesh_result_and_rolls_back():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.undoInfo.return_value = True
    cmds.objectType.side_effect = lambda node: "nurbsCurve" if "section" in node else "mesh"
    cmds.listRelatives.side_effect = lambda node, **kwargs: (
        ["{}Shape".format(node)] if str(node).startswith("section") else ["preExistingMeshShape"]
    )
    cmds.loft.return_value = ["preExistingMesh", "preExistingLoft"]
    uuid_by_node = {
        "preExistingMesh": "mesh-transform-old",
        "preExistingMeshShape": "mesh-shape-old",
        "preExistingLoft": "history-old",
    }

    def _ls(*args, **kwargs):
        if not kwargs.get("uuid"):
            return list(args)
        if args:
            return [uuid_by_node.get(str(args[0]), "input-{}".format(args[0]))]
        return ["mesh-transform-old", "mesh-shape-old", "history-old", "input-sectionA", "input-sectionB"]

    cmds.ls.side_effect = _ls

    result = load_and_call(
        "maya-mesh-ops/scripts/loft_sections.py",
        cmds,
        "main",
        sections=["sectionA", "sectionB"],
    )

    assert result["success"] is False
    assert result["context"]["rollback_verified"] is True
    cmds.undo.assert_called_once_with()


def test_lathe_profile_rejects_preexisting_mesh_result_and_rolls_back():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.undoInfo.return_value = True
    cmds.objectType.side_effect = lambda node: "nurbsCurve" if "profile" in node else "mesh"
    cmds.listRelatives.side_effect = lambda node, **kwargs: (
        ["profileShape"] if node == "profile" else ["preExistingMeshShape"]
    )
    cmds.revolve.return_value = ["preExistingMesh", "preExistingRevolve"]
    uuid_by_node = {
        "preExistingMesh": "mesh-transform-old",
        "preExistingMeshShape": "mesh-shape-old",
        "preExistingRevolve": "history-old",
    }

    def _ls(*args, **kwargs):
        if not kwargs.get("uuid"):
            return list(args)
        if args:
            return [uuid_by_node.get(str(args[0]), "profile-input")]
        return ["mesh-transform-old", "mesh-shape-old", "history-old", "profile-input"]

    cmds.ls.side_effect = _ls

    result = load_and_call(
        "maya-mesh-ops/scripts/lathe_profile.py",
        cmds,
        "main",
        profile="profile",
    )

    assert result["success"] is False
    assert result["context"]["rollback_verified"] is True
    cmds.undo.assert_called_once_with()


def test_set_pivot_reads_back_both_maya_pivots():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.undoInfo.return_value = True
    cmds.xform.side_effect = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        None,
        [1.0, 2.0, 3.0, 1.0, 2.0, 3.0],
    ]

    result = load_and_call(
        "maya-mesh-ops/scripts/set_pivot.py",
        cmds,
        "main",
        object_name="rotor",
        position=[1.0, 2.0, 3.0],
        space="world",
    )

    assert result["success"] is True, result
    assert result["context"]["rotate_pivot"] == [1.0, 2.0, 3.0]
    assert result["context"]["scale_pivot"] == [1.0, 2.0, 3.0]


def test_set_pivot_fails_closed_when_readback_does_not_match():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.undoInfo.return_value = True
    cmds.xform.side_effect = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        None,
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ]

    result = load_and_call(
        "maya-mesh-ops/scripts/set_pivot.py",
        cmds,
        "main",
        object_name="rotor",
        position=[1.0, 2.0, 3.0],
    )

    assert result["success"] is False
    assert "verification" in result["message"].lower()


def test_auto_uv_requires_positive_uv_readback():
    failed_cmds = MagicMock()
    failed_cmds.objExists.return_value = True
    failed_cmds.undoInfo.return_value = True
    failed_cmds.polyUVSet.return_value = ["map1"]
    failed_cmds.polyEvaluate.side_effect = [0, 0, 0]
    failed_cmds.polyEditUV.return_value = []

    failed = load_and_call(
        "maya-uv-ops/scripts/auto_uv.py",
        failed_cmds,
        "main",
        object_name="body",
        planes=6,
    )

    succeeded_cmds = MagicMock()
    succeeded_cmds.objExists.return_value = True
    succeeded_cmds.undoInfo.return_value = True
    succeeded_cmds.polyUVSet.return_value = ["map1"]
    succeeded_cmds.polyEvaluate.side_effect = [0, 128]
    succeeded_cmds.polyEditUV.side_effect = [[], [float(index) / 255 for index in range(256)]]
    succeeded = load_and_call(
        "maya-uv-ops/scripts/auto_uv.py",
        succeeded_cmds,
        "main",
        object_name="body",
        planes=6,
    )

    assert failed["success"] is False
    assert failed["context"]["rollback_verified"] is True
    assert succeeded["success"] is True, succeeded
    assert succeeded["context"]["uv_count"] == 128
    assert succeeded["context"]["changed"] is True


def test_auto_uv_rejects_positive_but_unchanged_uv_state_and_rolls_back():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.undoInfo.return_value = True
    cmds.polyUVSet.return_value = ["map1"]
    cmds.polyEvaluate.return_value = 2
    cmds.polyEditUV.return_value = [0.0, 0.0, 1.0, 1.0]

    result = load_and_call(
        "maya-uv-ops/scripts/auto_uv.py",
        cmds,
        "main",
        object_name="body",
        planes=6,
    )

    assert result["success"] is False
    assert result["context"]["rollback_verified"] is True
    cmds.undo.assert_called_once_with()


def test_auto_uv_rejects_plane_counts_not_supported_by_maya():
    skills_root = SKILL_ROOT.parent
    tools = yaml.safe_load((skills_root / "maya-uv-ops" / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    contract = next(item for item in tools if item["name"] == "auto_uv")
    assert contract["input_schema"]["properties"]["planes"]["enum"] == [4, 5, 6, 8, 12]

    cmds = MagicMock()
    result = load_and_call(
        "maya-uv-ops/scripts/auto_uv.py",
        cmds,
        "main",
        object_name="body",
        planes=7,
    )

    assert result["success"] is False
    cmds.polyAutoProjection.assert_not_called()


def test_existing_modeling_deltas_publish_typed_readback_contracts():
    skills_root = SKILL_ROOT.parent
    expected = {
        "maya-mesh-ops": ("mirror_mesh", {"faces_before", "faces_after"}),
        "maya-scene": ("freeze_transforms", {"verified_transform"}),
        "maya-node-graph": ("delete_history", {"remaining_history", "removed_count"}),
        "maya-uv-ops": ("auto_uv", {"uv_count", "planes"}),
        "maya-materials": ("assign_material", {"verified_objects", "verified_count"}),
    }

    for skill_name, (tool_name, required_output) in expected.items():
        tools = yaml.safe_load((skills_root / skill_name / "tools.yaml").read_text(encoding="utf-8"))["tools"]
        contract = next(item for item in tools if item["name"] == tool_name)
        assert contract["affinity"] == "main"
        assert contract["input_schema"]["additionalProperties"] is False
        assert required_output <= set(contract["output_schema"]["required"])

    material_tools = yaml.safe_load((skills_root / "maya-materials" / "tools.yaml").read_text(encoding="utf-8"))[
        "tools"
    ]
    assign = next(item for item in material_tools if item["name"] == "assign_material")
    array_variant = next(
        variant
        for variant in assign["input_schema"]["properties"]["objects"]["oneOf"]
        if variant.get("type") == "array"
    )
    assert array_variant["maxItems"] == 256
