"""Unit tests for the maya-bifrost graph-authoring skill."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest
from conftest import load_and_call

from dcc_mcp_maya.bifrost import (
    BifrostContractError,
    add_node,
    compound_node_path,
    connect_ports,
    create_graph,
    create_port,
    encode_default_value,
    list_graphs,
    set_port_default,
)
from dcc_mcp_maya.procedural_house import (
    HOUSE_STYLES,
    HouseContractError,
    build_house_graph,
    design_house,
    house_spec_to_dict,
)


def _bifrost_graph_cmds() -> MagicMock:
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "bifrostGraphShape"
    return cmds


def _house_cmds() -> MagicMock:
    cmds = _bifrost_graph_cmds()
    cmds.createNode.return_value = "houseShape"
    cmds.listRelatives.return_value = ["|house"]
    cmds.exactWorldBoundingBox.return_value = [-3.0, 0.0, -2.5, 3.0, 6.0, 2.5]
    created_nodes = []

    def vnn_compound(*_args, **kwargs):
        if "addNode" in kwargs:
            return [kwargs["addNode"].rsplit(",", 1)[-1]]
        if "renameNode" in kwargs:
            created_nodes.append(kwargs["renameNode"][1])
            return [kwargs["renameNode"][1]]
        if kwargs.get("listNodes"):
            return ["input"] + created_nodes + ["output"]
        return None

    cmds.vnnCompound.side_effect = vnn_compound
    return cmds


def test_create_graph_returns_shape_and_transform() -> None:
    cmds = MagicMock()
    cmds.createNode.return_value = "houseShape"
    cmds.listRelatives.return_value = ["|house"]

    result = create_graph(cmds, name="houseShape", kind="graph_shape")

    cmds.createNode.assert_called_once_with("bifrostGraphShape", name="houseShape")
    cmds.setAttr.assert_called_once_with("houseShape.displayFinalInViewport", True)
    cmds.sets.assert_called_once_with("houseShape", edit=True, forceElement="initialShadingGroup")
    assert result == {
        "graph": "houseShape",
        "node_type": "bifrostGraphShape",
        "kind": "graph_shape",
        "transform": "|house",
    }


def test_add_node_uses_fully_qualified_bifrost_type_and_renames() -> None:
    cmds = _bifrost_graph_cmds()
    cmds.vnnCompound.side_effect = [["create_mesh_cube"], None]

    node = add_node(
        cmds,
        "houseShape",
        "Modeling::Primitive::create_mesh_cube",
        name="walls",
    )

    assert node == "walls"
    assert cmds.vnnCompound.call_args_list[0][1] == {"addNode": "BifrostGraph,Modeling::Primitive,create_mesh_cube"}
    assert cmds.vnnCompound.call_args_list[1][1] == {"renameNode": ("create_mesh_cube", "walls")}


def test_set_port_default_encodes_vector_values() -> None:
    cmds = _bifrost_graph_cmds()

    result = set_port_default(cmds, "houseShape", "walls", "position", [-2.5, 1.0, 0.0])

    cmds.vnnNode.assert_called_once_with(
        "houseShape",
        ".walls",
        setPortDefaultValues=("position", "{-2.5, 1.0, 0.0}"),
    )
    assert result["encoded_value"] == "{-2.5, 1.0, 0.0}"
    assert encode_default_value(True) == "1"
    assert encode_default_value(["front", "back"]) == "{'front', 'back'}"


def test_compound_node_path_uses_vnn_nested_path_convention() -> None:
    assert compound_node_path(".", "cube") == ".cube"
    assert compound_node_path("facade", "window") == "/facade/window"


def test_connect_ports_normalizes_paths_and_disconnects() -> None:
    cmds = _bifrost_graph_cmds()

    result = connect_ports(
        cmds,
        "houseShape",
        "walls.cube_mesh",
        "output.house",
        disconnect=True,
        copy_metadata=True,
    )

    cmds.vnnConnect.assert_called_once_with(
        "houseShape",
        ".walls.cube_mesh",
        ".output.house",
        disconnect=True,
        copyMetaData=True,
    )
    assert result["disconnected"] is True


def test_create_port_uses_direction_specific_vnn_flag() -> None:
    cmds = _bifrost_graph_cmds()
    cmds.vnnNode.side_effect = [None, ["house_parts.part_0", "house_parts.array"]]

    result = create_port(
        cmds,
        "houseShape",
        "house_parts",
        "part_0",
        "Object",
        direction="input",
    )

    assert cmds.vnnNode.call_args_list == [
        call("houseShape", ".house_parts", createInputPort=("part_0", "Object")),
        call("houseShape", ".house_parts", listPorts=True),
    ]
    assert result["direction"] == "input"


def test_create_port_normalizes_object_array_for_legacy_vnn() -> None:
    cmds = _bifrost_graph_cmds()
    cmds.vnnNode.side_effect = [None, ["output.other"], None]

    create_port(cmds, "houseShape", "output", "geometry", "array<Object>", direction="output")

    assert cmds.vnnNode.call_args_list == [
        call("houseShape", ".output", createOutputPort=("geometry", "array<Object>")),
        call("houseShape", ".output", listPorts=True),
        call("houseShape", ".output", createOutputPort=("geometry", "array<Amino::Object>")),
    ]


def test_list_graphs_includes_nodes_and_ports() -> None:
    cmds = MagicMock()
    cmds.ls.side_effect = lambda **kwargs: ["|house|houseShape"] if kwargs["type"] == "bifrostGraphShape" else []
    cmds.listRelatives.return_value = ["|house"]
    cmds.vnnCompound.return_value = ["input", "walls", "output"]
    cmds.vnnNode.side_effect = lambda _graph, node, **_kwargs: [node + ".port"]

    result = list_graphs(cmds, include_nodes=True, include_ports=True)

    assert result[0]["node_count"] == 3
    assert result[0]["ports"]["walls"] == [".walls.port"]


def test_graph_validation_rejects_non_bifrost_nodes() -> None:
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "mesh"

    with pytest.raises(BifrostContractError, match="expected one of"):
        connect_ports(cmds, "pCubeShape1", ".a.out", ".b.in")


def test_create_bifrost_graph_skill_loads_plugins_and_returns_typed_context() -> None:
    cmds = MagicMock()
    cmds.pluginInfo.side_effect = lambda _plugin, **kwargs: "2.14.0" if kwargs.get("version") else True
    cmds.createNode.return_value = "houseShape"
    cmds.listRelatives.return_value = ["|house"]

    result = load_and_call(
        "maya-bifrost/scripts/create_bifrost_graph.py",
        cmds,
        "main",
        name="houseShape",
        kind="graph_shape",
    )

    assert result["success"] is True, result
    assert result["context"]["graph"] == "houseShape"
    assert result["context"]["runtime"]["bifrost_version"] == "2.14.0"


def test_house_design_is_seeded_and_supports_distinct_styles() -> None:
    first = design_house(seed=42, style="random", position=(10, 0, -4))
    second = design_house(seed=42, style="random", position=(10, 0, -4))

    assert first == second
    assert first.style in HOUSE_STYLES
    assert house_spec_to_dict(first)["seed"] == 42
    assert any(part.anchor[0] >= 10 for part in first.parts)
    assert any(part.kind == "gable" for part in design_house(seed=7, style="cabin").parts)
    assert all(part.kind == "cube" for part in design_house(seed=7, style="modern").parts)


def test_house_design_rejects_invalid_style_and_position() -> None:
    with pytest.raises(HouseContractError, match="style must be one of"):
        design_house(seed=1, style="castle")
    with pytest.raises(HouseContractError, match="exactly three"):
        design_house(seed=1, position=(1, 2))


def test_build_house_graph_uses_bifrost_primitives_array_and_merge() -> None:
    cmds = _house_cmds()
    spec = design_house(seed=11, style="cottage")

    result = build_house_graph(cmds, spec, name="Demo House")

    add_node_contracts = [call[1]["addNode"] for call in cmds.vnnCompound.call_args_list if "addNode" in call[1]]
    assert "BifrostGraph,Modeling::Primitive,create_mesh_cube" in add_node_contracts
    assert add_node_contracts.count("BifrostGraph,Modeling::Primitive,create_mesh_cube") >= 3
    assert "BifrostGraph,Modeling::Points,transform_points" in add_node_contracts
    assert "BifrostGraph,Core::Array,build_array" in add_node_contracts
    assert "BifrostGraph,Modeling::Common,merge_geometry" in add_node_contracts
    assert result["name"] == "Demo_House"
    assert result["style"] == "cottage"
    assert result["part_count"] == len(spec.parts)
    assert result["bounds"] == [-3.0, 0.0, -2.5, 3.0, 6.0, 2.5]
    walls = spec.parts[0]
    assert any(
        call[0][1] == ".walls"
        and call[1].get("setPortDefaultValues") == ("width", encode_default_value(walls.dimensions[0]))
        for call in cmds.vnnNode.call_args_list
    )
    assert any(
        call[0][1] == ".walls"
        and call[1].get("setPortDefaultValues") == ("length", encode_default_value(walls.dimensions[2]))
        for call in cmds.vnnNode.call_args_list
    )
    assert any(call[0][1:] == (".merge_house.merged", ".output.house") for call in cmds.vnnConnect.call_args_list)
    assert cmds.setAttr.call_args_list[-2:] == [
        call("houseShape.displayFinalInViewport", False),
        call("houseShape.displayFinalInViewport", True),
    ]


def test_generate_procedural_house_skill_returns_seed_and_graph() -> None:
    cmds = _house_cmds()
    cmds.pluginInfo.side_effect = lambda _plugin, **kwargs: "2.14.0" if kwargs.get("version") else True

    result = load_and_call(
        "maya-bifrost/scripts/generate_procedural_house.py",
        cmds,
        "main",
        seed=123,
        style="modern",
        name="Modern Demo",
    )

    assert result["success"] is True, result
    assert result["context"]["seed"] == 123
    assert result["context"]["style"] == "modern"
    assert result["context"]["graph"] == "houseShape"
    cmds.select.assert_called_once_with("|house", replace=True)
