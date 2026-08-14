"""Contract tests for native-editable and fidelity-first Maya Asset Sync."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).parents[1]
_SKILL = _ROOT / "src" / "dcc_mcp_maya" / "skills" / "maya-asset-sync"


def _module():
    spec = importlib.util.spec_from_file_location("maya_asset_sync_test", _SKILL / "scripts" / "asset_sync.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_rig_cmds():
    class FakeCmds:
        controllers = {
            "|asset|wingL_CTRL": "wing.left.front",
            "|asset|wingR_CTRL": "wing.right.front",
        }
        constraints = {
            "|asset|wingL_orientConstraint1": {
                "drivers": ["|asset|wingL_CTRL"],
                "driven": "|asset|wingL_joint",
                "aliases": ["wingLW0"],
                "weights": {"wingLW0": 1.0},
            },
            "|asset|wingR_orientConstraint1": {
                "drivers": ["|asset|wingR_CTRL"],
                "driven": "|asset|wingR_joint",
                "aliases": ["wingRW0"],
                "weights": {"wingRW0": 1.0},
            },
        }
        locked_controllers = set()
        locked_weight_aliases = set()
        broken_constraints = set()
        attribute_flag_failures = set()
        attribute_value_failures = set()

        @classmethod
        def ls(cls, *nodes, type=None, long=False):
            if nodes:
                return [str(nodes[0])]
            if type == "transform":
                # Real Maya includes constraint DAG nodes in this query.
                return list(cls.controllers) + list(cls.constraints)
            if type == "orientConstraint":
                return list(cls.constraints)
            return []

        @classmethod
        def attributeQuery(cls, attribute, node=None, exists=False):
            assert exists is True
            return (
                attribute == "dccMcpControllerRole" and (node in cls.controllers or node in cls.constraints)
            ) or attribute in {
                "translateX",
                "translateY",
                "translateZ",
                "rotateX",
                "rotateY",
                "rotateZ",
                "scaleX",
                "scaleY",
                "scaleZ",
            }

        @classmethod
        def objExists(cls, _plug):
            return False

        @classmethod
        def getAttr(cls, plug, lock=False, keyable=False):
            node, attribute = plug.rsplit(".", 1)
            if attribute == "dccMcpControllerRole" and not lock and not keyable:
                if node in cls.controllers:
                    return cls.controllers[node]
                driver = cls.constraints[node]["drivers"][0]
                return cls.controllers[driver]
            failure_flag = "lock" if lock else "keyable" if keyable else None
            if failure_flag and (plug, failure_flag) in cls.attribute_flag_failures:
                raise RuntimeError(plug)
            if plug in cls.attribute_value_failures:
                raise RuntimeError(plug)
            if node in cls.constraints and attribute in cls.constraints[node]["weights"]:
                if lock:
                    return plug in cls.locked_weight_aliases
                if keyable:
                    return False
                return cls.constraints[node]["weights"][attribute]
            if lock:
                return node in cls.locked_controllers
            if keyable:
                return node in cls.controllers
            raise RuntimeError(plug)

        @classmethod
        def listRelatives(cls, node, **kwargs):
            assert kwargs == {
                "shapes": True,
                "noIntermediate": True,
                "fullPath": True,
                "type": "nurbsCurve",
            }
            if node in cls.constraints:
                return []
            return [node + "|" + node.rsplit("|", 1)[-1] + "Shape"]

        @classmethod
        def orientConstraint(cls, node, query=False, targetList=False, weightAliasList=False):
            assert query is True
            record = cls.constraints[node]
            if targetList:
                return list(record["drivers"])
            if weightAliasList:
                return list(record["aliases"])
            raise AssertionError(node)

        @classmethod
        def listConnections(cls, node_or_plug, **kwargs):
            if node_or_plug in cls.constraints:
                assert kwargs == {
                    "source": False,
                    "destination": True,
                    "plugs": True,
                }
                if node_or_plug in cls.broken_constraints:
                    return []
                return [cls.constraints[node_or_plug]["driven"] + ".rotateX"]
            assert kwargs == {
                "source": True,
                "destination": False,
                "type": "animCurve",
            }
            return ["wing_animCurve"] if node_or_plug.endswith(".rotateZ") else []

    return FakeCmds


def test_source_name_is_confined_to_operator_root(tmp_path: Path) -> None:
    module = _module()
    assert module._safe_relative(tmp_path, "exports/bee.usdc") == tmp_path / "exports" / "bee.usdc"
    with pytest.raises(ValueError, match="safe relative"):
        module._safe_relative(tmp_path, "../secret.usdc")
    with pytest.raises(ValueError, match="safe relative"):
        module._safe_relative(tmp_path, str(tmp_path / "absolute.usdc"))


def test_sync_schema_exposes_deliberate_editability_modes() -> None:
    tools = yaml.safe_load((_SKILL / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    by_name = {tool["name"]: tool for tool in tools}
    assert set(by_name) == {"publish_usd_revision", "read_asset_head", "sync_usd_revision"}
    sync_schema = by_name["sync_usd_revision"]["input_schema"]
    assert sync_schema["additionalProperties"] is False
    assert sync_schema["properties"]["editability_mode"]["enum"] == ["native", "usd_proxy"]
    assert sync_schema["properties"]["rig_expectation"]["enum"] == ["auto", "ignore", "skeleton", "skinned"]
    controller_roles = sync_schema["properties"]["required_constrained_controller_roles"]
    assert "required_constrained_controller_roles" not in sync_schema["required"]
    assert controller_roles["default"] == []
    assert controller_roles["maxItems"] == 64
    assert controller_roles["uniqueItems"] is True
    assert controller_roles["items"]["maxLength"] == 64
    publish_properties = by_name["publish_usd_revision"]["input_schema"]["properties"]
    assert "source_name" in publish_properties
    assert "source_path" not in publish_properties
    assert "store_root" not in publish_properties


def test_native_sync_reports_arnold_pbr_evidence() -> None:
    source = (_SKILL / "scripts" / "asset_sync.py").read_text(encoding="utf-8")
    assert '"preferredMaterial": "standardSurface"' in source
    assert '"arnold_standard_surface_materials"' in source
    assert '"pbr_materials"' in source
    assert '"specular_ior"' in source
    assert '"connected_inputs"' in source
    assert '"image_textures"' in source
    assert '"image_texture_evidence_truncated"' in source


def test_image_texture_evidence_reports_paths_color_spaces_and_material_inputs(tmp_path: Path) -> None:
    module = _module()
    source_image = tmp_path / "sourceimages" / "bee" / "albedo.png"
    source_image.parent.mkdir(parents=True)
    source_image.write_bytes(b"texture")
    normal_image = tmp_path / "normal.exr"
    normal_image.write_bytes(b"texture")

    class FakeCmds:
        types = {
            "BeeAlbedo": "file",
            "BeeColorCorrect": "aiColorCorrect",
            "BeeNormal": "aiImage",
            "BeeNormalMap": "aiNormalMap",
            "BeeMat": "standardSurface",
        }
        attrs = {
            "BeeAlbedo.fileTextureName": "bee/albedo.png",
            "BeeAlbedo.colorSpace": "sRGB",
            "BeeNormal.filename": str(normal_image),
            "BeeNormal.colorSpace": "Raw",
        }
        downstream = {
            "BeeAlbedo": ["BeeAlbedo.outColor", "BeeColorCorrect.input"],
            "BeeColorCorrect": ["BeeColorCorrect.outColor", "BeeMat.baseColor"],
            "BeeNormal": ["BeeNormal.outColor", "BeeNormalMap.input"],
            "BeeNormalMap": ["BeeNormalMap.outValue", "BeeMat.normalCamera"],
        }

        @classmethod
        def ls(cls, materials=False, **_kwargs):
            return ["BeeMat"] if materials else []

        @classmethod
        def nodeType(cls, node):
            return cls.types[node]

        @classmethod
        def getAttr(cls, plug):
            if plug not in cls.attrs:
                raise RuntimeError(plug)
            return cls.attrs[plug]

        @classmethod
        def workspace(cls, query=False, rootDirectory=False, fileRuleEntry=None):
            if query and rootDirectory:
                return str(tmp_path)
            if fileRuleEntry == "sourceImages":
                return "sourceimages"
            raise AssertionError((query, rootDirectory, fileRuleEntry))

        @classmethod
        def listConnections(cls, node, **kwargs):
            assert kwargs == {
                "source": False,
                "destination": True,
                "plugs": True,
                "connections": True,
            }
            return cls.downstream.get(node, [])

        @classmethod
        def objectType(cls, _node, isAType=None):
            assert isAType == "dagNode"
            return False

    imported = {"BeeAlbedo", "BeeColorCorrect", "BeeNormal", "BeeNormalMap", "BeeMat"}
    result = module._image_texture_evidence(FakeCmds, ["BeeNormal", "BeeAlbedo"], imported)

    assert result == {
        "records": [
            {
                "node": "BeeAlbedo",
                "type": "file",
                "path": "bee/albedo.png",
                "path_attr": "fileTextureName",
                "exists": True,
                "color_space": "sRGB",
                "is_absolute": False,
                "workspace_relative_path": "sourceimages/bee/albedo.png",
                "under_workspace": True,
                "imported": True,
                "connected_material_inputs": [
                    {
                        "material": "BeeMat",
                        "input": "baseColor",
                        "plug": "BeeMat.baseColor",
                        "direct": False,
                        "via": ["BeeColorCorrect"],
                        "material_imported": True,
                    }
                ],
                "connections_truncated": False,
            },
            {
                "node": "BeeNormal",
                "type": "aiImage",
                "path": str(normal_image),
                "path_attr": "filename",
                "exists": True,
                "color_space": "Raw",
                "is_absolute": True,
                "workspace_relative_path": "normal.exr",
                "under_workspace": True,
                "imported": True,
                "connected_material_inputs": [
                    {
                        "material": "BeeMat",
                        "input": "normalCamera",
                        "plug": "BeeMat.normalCamera",
                        "direct": False,
                        "via": ["BeeNormalMap"],
                        "material_imported": True,
                    }
                ],
                "connections_truncated": False,
            },
        ],
        "total": 2,
        "limit": module._IMAGE_TEXTURE_EVIDENCE_LIMIT,
        "truncated": False,
    }


def test_image_texture_evidence_is_bounded_and_prioritizes_imported_nodes(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(module, "_IMAGE_TEXTURE_EVIDENCE_LIMIT", 2)

    class FakeCmds:
        @staticmethod
        def ls(materials=False, **_kwargs):
            return []

        @staticmethod
        def nodeType(_node):
            return "file"

        @staticmethod
        def getAttr(plug):
            if plug.endswith(".fileTextureName"):
                return ""
            if plug.endswith(".colorSpace"):
                return "Raw"
            raise RuntimeError(plug)

        @staticmethod
        def workspace(**_kwargs):
            raise RuntimeError("workspace unavailable")

        @staticmethod
        def listConnections(_node, **_kwargs):
            return []

    result = module._image_texture_evidence(FakeCmds, ["OldB", "New", "OldA"], {"New"})

    assert [record["node"] for record in result["records"]] == ["New", "OldA"]
    assert result["total"] == 3
    assert result["limit"] == 2
    assert result["truncated"] is True


def test_image_texture_evidence_marks_external_absolute_path_outside_workspace(tmp_path: Path) -> None:
    module = _module()
    external_root = tmp_path.parent / f"{tmp_path.name}_external"
    external_root.mkdir()
    external_texture = external_root / "normal.exr"
    external_texture.write_bytes(b"texture")

    class FakeCmds:
        @staticmethod
        def ls(materials=False, **_kwargs):
            return []

        @staticmethod
        def nodeType(_node):
            return "aiImage"

        @staticmethod
        def getAttr(plug):
            if plug.endswith(".filename"):
                return str(external_texture)
            if plug.endswith(".colorSpace"):
                return "Raw"
            raise RuntimeError(plug)

        @staticmethod
        def workspace(query=False, rootDirectory=False, fileRuleEntry=None):
            if query and rootDirectory:
                return str(tmp_path)
            if fileRuleEntry == "sourceImages":
                return "sourceimages"
            raise AssertionError((query, rootDirectory, fileRuleEntry))

        @staticmethod
        def listConnections(_node, **_kwargs):
            return []

    result = module._image_texture_evidence(FakeCmds, ["ExternalNormal"], {"ExternalNormal"})
    record = result["records"][0]

    assert record["exists"] is True
    assert record["is_absolute"] is True
    assert record["workspace_relative_path"] is None
    assert record["under_workspace"] is False


def test_texture_existence_accepts_common_udim_tokens(tmp_path: Path) -> None:
    module = _module()
    (tmp_path / "bee_albedo.1001.exr").write_bytes(b"texture")

    assert module._path_or_sequence_exists(tmp_path / "bee_albedo.<UDIM>.exr") is True
    assert module._path_or_sequence_exists(tmp_path / "missing.<UDIM>.exr") is False


def test_native_sync_audits_standard_rig_preservation() -> None:
    source = (_SKILL / "scripts" / "asset_sync.py").read_text(encoding="utf-8")
    tools = (_SKILL / "tools.yaml").read_text(encoding="utf-8")
    assert "def _usd_rig_evidence" in source
    assert '"skin_clusters": count_type("skinCluster")' in source
    assert 'rig_expectation: str = "auto"' in source
    assert 'evidence["joints"] == 0' in source
    assert 'evidence["skin_clusters"] == 0' in source
    assert "def _rig_editability_evidence" in source
    assert '"rig_editability"' in source
    assert "dccMcpControllerRole" in source
    assert "required_constrained_controller_roles" in source
    assert "_required_controller_failures" in source
    assert "rig_expectation:" in tools
    assert "- skinned" in tools
    assert "required_constrained_controller_roles:" in tools


def test_controller_roles_are_normalized_and_strictly_bounded() -> None:
    module = _module()

    assert module._normalize_required_controller_roles(None) == []
    assert module._normalize_required_controller_roles([]) == []
    assert module._normalize_required_controller_roles(["wing.right.front", "wing.left.front"]) == [
        "wing.left.front",
        "wing.right.front",
    ]
    with pytest.raises(ValueError, match="array"):
        module._normalize_required_controller_roles("wing.left.front")
    with pytest.raises(ValueError, match="unique"):
        module._normalize_required_controller_roles(["wing.left.front", "wing.left.front"])
    with pytest.raises(ValueError, match="identifier"):
        module._normalize_required_controller_roles(["wing left"])
    with pytest.raises(ValueError, match="strings"):
        module._normalize_required_controller_roles([None])
    with pytest.raises(ValueError, match="at most 64"):
        module._normalize_required_controller_roles(["wing.role.{}".format(index) for index in range(65)])


def test_rig_editability_reports_sorted_native_controller_and_constraint_records() -> None:
    module = _module()
    cmds = _fake_rig_cmds()

    evidence = module._rig_editability_evidence(
        cmds,
        {"|asset"},
        ["wing.right.front", "wing.left.front"],
    )

    assert evidence["role_attribute"] == "dccMcpControllerRole"
    assert [record["role"] for record in evidence["controllers"]["records"]] == [
        "wing.left.front",
        "wing.right.front",
    ]
    assert [record["node"] for record in evidence["constraints"]["records"]] == [
        "|asset|wingL_orientConstraint1",
        "|asset|wingR_orientConstraint1",
    ]
    assert all(record["shape_type"] == "nurbsCurve" for record in evidence["controllers"]["records"])
    assert all(record["editable"] for record in evidence["controllers"]["records"])
    assert all(record["editable"] for record in evidence["constraints"]["records"])
    assert all(not record["unknown_channel_states"] for record in evidence["controllers"]["records"])
    assert all(record["editable_driven_constraints"] for record in evidence["controllers"]["records"])
    assert all(record["target_weight_mapping_complete"] for record in evidence["constraints"]["records"])
    assert evidence["controllers"]["total"] == 2
    assert evidence["controllers"]["truncated"] is False
    assert evidence["constraints"]["total"] == 2
    assert evidence["constraints"]["truncated"] is False
    assert evidence["missing_roles"] == []
    assert evidence["duplicate_roles"] == []
    assert evidence["non_editable_roles"] == []
    assert evidence["unconstrained_roles"] == []
    assert evidence["all_required_editable"] is True
    assert evidence["all_required_constrained"] is True
    assert module._required_controller_failures(evidence) == []


def test_explicit_controller_roles_fail_closed_with_precise_evidence() -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    cmds.locked_controllers.add("|asset|wingL_CTRL")
    cmds.broken_constraints.add("|asset|wingR_orientConstraint1")

    evidence = module._rig_editability_evidence(
        cmds,
        {"|asset"},
        ["wing.missing", "wing.left.front", "wing.right.front"],
    )

    assert evidence["missing_roles"] == ["wing.missing"]
    assert evidence["non_editable_roles"] == ["wing.left.front"]
    assert evidence["unconstrained_roles"] == ["wing.right.front"]
    assert evidence["all_required_editable"] is False
    assert evidence["all_required_constrained"] is False
    assert module._required_controller_failures(evidence) == [
        "missing controller roles: wing.missing",
        "non-editable controller roles: wing.left.front",
        "unconstrained controller roles: wing.right.front",
    ]


def test_controller_records_are_bounded_and_prioritize_explicit_roles(monkeypatch) -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    monkeypatch.setattr(module, "_CONTROLLER_EVIDENCE_LIMIT", 1)

    evidence = module._rig_editability_evidence(
        cmds,
        {"|asset"},
        ["wing.right.front"],
    )

    assert evidence["controllers"]["total"] == 2
    assert evidence["controllers"]["limit"] == 1
    assert evidence["controllers"]["truncated"] is True
    assert [record["role"] for record in evidence["controllers"]["records"]] == ["wing.right.front"]
    assert evidence["all_required_constrained"] is True


def test_multi_target_constraint_preserves_target_weight_alias_order() -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    cmds.controllers = {
        "|asset|z_CTRL": "wing.required",
        "|asset|a_CTRL": "wing.other",
    }
    cmds.constraints = {
        "|asset|multi_orientConstraint1": {
            "drivers": ["|asset|z_CTRL", "|asset|a_CTRL"],
            "driven": "|asset|wing_joint",
            # Deliberately opposite lexical order. Maya pairs these lists by index.
            "aliases": ["z_CTRLW0", "a_CTRLW1"],
            "weights": {"z_CTRLW0": 0.0, "a_CTRLW1": 1.0},
        }
    }
    cmds.locked_weight_aliases.add("|asset|multi_orientConstraint1.z_CTRLW0")

    evidence = module._rig_editability_evidence(cmds, {"|asset"}, ["wing.required"])
    constraint = evidence["constraints"]["records"][0]
    targets = {record["driver"]: record for record in constraint["target_weights"]}

    assert targets["|asset|z_CTRL"]["weight_alias"] == "z_CTRLW0"
    assert targets["|asset|z_CTRL"]["locked"] is True
    assert targets["|asset|z_CTRL"]["editable"] is False
    assert targets["|asset|a_CTRL"]["weight_alias"] == "a_CTRLW1"
    assert targets["|asset|a_CTRL"]["editable"] is True
    assert evidence["unconstrained_roles"] == ["wing.required"]
    assert evidence["all_required_constrained"] is False


def test_controller_attribute_probe_failure_is_fail_closed() -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    channels = (
        "translateX",
        "translateY",
        "translateZ",
        "rotateX",
        "rotateY",
        "rotateZ",
        "scaleX",
        "scaleY",
        "scaleZ",
    )
    cmds.attribute_flag_failures.update(("|asset|wingL_CTRL." + channel, "lock") for channel in channels)

    evidence = module._rig_editability_evidence(cmds, {"|asset"}, ["wing.left.front"])
    controller = evidence["controllers"]["records"][0]

    assert controller["keyable_channels"] == []
    assert controller["unknown_channel_states"] == sorted(channels)
    assert controller["editable"] is False
    assert evidence["non_editable_roles"] == ["wing.left.front"]


@pytest.mark.parametrize("failure_kind", ["lock", "value"])
def test_constraint_weight_probe_failure_is_fail_closed(failure_kind: str) -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    plug = "|asset|wingL_orientConstraint1.wingLW0"
    if failure_kind == "lock":
        cmds.attribute_flag_failures.add((plug, "lock"))
    else:
        cmds.attribute_value_failures.add(plug)

    evidence = module._rig_editability_evidence(cmds, {"|asset"}, ["wing.left.front"])
    constraint = evidence["constraints"]["records"][0]

    assert constraint["unknown_weight_aliases"] == ["wingLW0"]
    assert constraint["target_weights"][0]["editable"] is False
    assert evidence["unconstrained_roles"] == ["wing.left.front"]
    assert evidence["all_required_constrained"] is False


def test_one_editable_constraint_relation_is_sufficient() -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    cmds.constraints["|asset|wingL_bad_orientConstraint1"] = {
        "drivers": ["|asset|wingL_CTRL"],
        "driven": "|asset|wingL_joint",
        "aliases": ["wingLBadW0"],
        "weights": {"wingLBadW0": 1.0},
    }
    cmds.locked_weight_aliases.add("|asset|wingL_bad_orientConstraint1.wingLBadW0")

    evidence = module._rig_editability_evidence(cmds, {"|asset"}, ["wing.left.front"])
    controller = evidence["controllers"]["records"][0]

    assert controller["driven_constraints"] == [
        "|asset|wingL_bad_orientConstraint1",
        "|asset|wingL_orientConstraint1",
    ]
    assert controller["editable_driven_constraints"] == ["|asset|wingL_orientConstraint1"]
    assert evidence["unconstrained_roles"] == []
    assert evidence["all_required_constrained"] is True


def test_unlocked_zero_weight_remains_editable() -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    cmds.constraints["|asset|wingL_orientConstraint1"]["weights"]["wingLW0"] = 0.0

    evidence = module._rig_editability_evidence(cmds, {"|asset"}, ["wing.left.front"])
    target = evidence["constraints"]["records"][0]["target_weights"][0]

    assert target["active"] is False
    assert target["editable"] is True
    assert evidence["all_required_constrained"] is True


def test_constraint_limit_round_robins_required_controllers(monkeypatch) -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    for index in range(4):
        alias = "wingLExtra{}W0".format(index)
        cmds.constraints["|asset|a_wingL_extra{}_orientConstraint1".format(index)] = {
            "drivers": ["|asset|wingL_CTRL"],
            "driven": "|asset|wingL_joint",
            "aliases": [alias],
            "weights": {alias: 1.0},
        }
    monkeypatch.setattr(module, "_CONSTRAINT_EVIDENCE_LIMIT", 2)

    evidence = module._rig_editability_evidence(
        cmds,
        {"|asset"},
        ["wing.left.front", "wing.right.front"],
    )
    recorded_drivers = {
        target["driver"] for constraint in evidence["constraints"]["records"] for target in constraint["target_weights"]
    }

    assert evidence["constraints"]["truncated"] is True
    assert recorded_drivers == {"|asset|wingL_CTRL", "|asset|wingR_CTRL"}
    assert evidence["all_required_constrained"] is True


def test_missing_target_weight_alias_is_fail_closed() -> None:
    module = _module()
    cmds = _fake_rig_cmds()
    cmds.constraints = {
        "|asset|multi_orientConstraint1": {
            "drivers": ["|asset|wingL_CTRL", "|asset|wingR_CTRL"],
            "driven": "|asset|wing_joint",
            "aliases": ["wingLW0"],
            "weights": {"wingLW0": 1.0},
        }
    }

    evidence = module._rig_editability_evidence(cmds, {"|asset"}, ["wing.right.front"])
    constraint = evidence["constraints"]["records"][0]
    targets = {record["driver"]: record for record in constraint["target_weights"]}

    assert constraint["target_weight_mapping_complete"] is False
    assert targets["|asset|wingR_CTRL"]["weight_alias"] is None
    assert targets["|asset|wingR_CTRL"]["editable"] is False
    assert evidence["all_required_constrained"] is False


def test_public_sync_rejects_missing_required_controller_evidence(monkeypatch, tmp_path: Path) -> None:
    module = _module()

    class Head:
        format = "usdc"
        metadata = {}
        digest = "digest"
        revision = 1

    class Store:
        def __init__(self, _root):
            pass

        @staticmethod
        def read_head(_channel_id, _asset_id):
            return Head()

        @staticmethod
        def materialize(_head, _root, subfolder=""):
            assert subfolder == ""
            return tmp_path / "bee.usdc"

    class FakeCmds:
        ls_calls = 0

        @classmethod
        def ls(cls, long=False):
            assert long is True
            cls.ls_calls += 1
            return [] if cls.ls_calls == 1 else ["|asset"]

        @staticmethod
        def mayaUSDImport(**_kwargs):
            return None

        @staticmethod
        def createNode(*_args, **_kwargs):
            raise AssertionError("metadata creation must not occur after a failed controller gate")

    monkeypatch.setitem(sys.modules, "maya", types.SimpleNamespace(cmds=FakeCmds))
    monkeypatch.setattr(module, "_core_types", lambda: (Store, object, object))
    monkeypatch.setattr(module, "_configured_root", lambda _name: tmp_path)
    monkeypatch.setattr(
        module,
        "_usd_rig_evidence",
        lambda _path: {"skeletons": 0, "animations": 0, "skinned_prims": 0},
    )
    monkeypatch.setattr(module, "_ensure_plugin", lambda _cmds, _name: None)
    monkeypatch.setattr(
        module,
        "_scene_evidence",
        lambda _cmds, _nodes, _roles: {
            "joints": 0,
            "skin_clusters": 0,
            "rig_editability": {
                "missing_roles": ["wing.left.front"],
                "duplicate_roles": [],
                "non_editable_roles": [],
                "unconstrained_roles": [],
            },
        },
    )

    result = module.sync_usd_revision(
        "main",
        "honeybee",
        rig_expectation="ignore",
        required_constrained_controller_roles=["wing.left.front"],
    )

    assert result["success"] is False
    assert result["message"] == "Maya did not preserve required constrained controllers"
    assert result["context"]["failures"] == ["missing controller roles: wing.left.front"]


def test_maya_namespace_uses_host_context_and_restores_it() -> None:
    module = _module()

    class FakeCmds:
        current = ":"
        namespaces = set()
        calls = []

        @classmethod
        def namespaceInfo(cls, currentNamespace=False):
            assert currentNamespace
            return cls.current

        @classmethod
        def namespace(cls, **kwargs):
            if "exists" in kwargs:
                return kwargs["exists"] in cls.namespaces
            if "add" in kwargs:
                cls.namespaces.add(kwargs["add"])
                cls.calls.append(("add", kwargs["add"]))
                return kwargs["add"]
            if "set" in kwargs:
                cls.current = kwargs["set"]
                cls.calls.append(("set", kwargs["set"]))
                return kwargs["set"]
            raise AssertionError(kwargs)

    with module._maya_namespace(FakeCmds, "HB18"):
        assert FakeCmds.current == "HB18"
    assert FakeCmds.current == ":"
    assert FakeCmds.calls == [("add", "HB18"), ("set", "HB18"), ("set", ":")]


def test_maya_namespace_restores_after_import_failure() -> None:
    module = _module()

    class FakeCmds:
        current = ":root"

        @classmethod
        def namespaceInfo(cls, currentNamespace=False):
            return cls.current

        @classmethod
        def namespace(cls, **kwargs):
            if "exists" in kwargs:
                return True
            if "set" in kwargs:
                cls.current = kwargs["set"]
                return cls.current
            raise AssertionError(kwargs)

    with pytest.raises(RuntimeError, match="import failed"):
        with module._maya_namespace(FakeCmds, "bee"):
            raise RuntimeError("import failed")
    assert FakeCmds.current == ":root"
