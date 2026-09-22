"""Unit tests for the compositing contract and the maya-compositing skill.

The fake ``cmds`` mirrors Maya 2025 behaviour verified against a real
interpreter: ``layeredTexture.inputs`` reports size 0 before the first
connection, and ``listConnections(plugs=True)`` on the array returns the source
plugs rather than the destination elements - both of which make the obvious
index derivations wrong.
"""

from __future__ import annotations

import pytest
from conftest import load_and_call

from dcc_mcp_maya.compositing import (
    BLEND_MODES,
    INPUT_PLUGS,
    MERGE_OPS,
    MULTIPLY_DIVIDE_OPS,
    UTILITY_NODES,
    CompositingContractError,
    add_layer,
    connect_comp,
    create_comp_node,
    create_image_reader,
    create_layer_stack,
    list_layers,
    merge_layers,
    remove_layer,
)


class _FakeCmds:
    """Stand-in for ``maya.cmds`` modelling Maya's comp node behaviour."""

    def __init__(self):
        self.nodes = {}
        self.connections = {}
        self.calls = []
        self._counter = {}

    def _new(self, node_type, name=None):
        self._counter[node_type] = self._counter.get(node_type, 0) + 1
        node = name or "{}{}".format(node_type, self._counter[node_type])
        self.nodes[node] = node_type
        return node

    def createNode(self, node_type, name=None):
        self.calls.append(("createNode", node_type, name))
        return self._new(node_type, name)

    @staticmethod
    def _split(plug):
        """Split ``node.attr`` on the FIRST dot.

        Compound plugs such as ``stack.inputs[0].blendMode`` contain more than
        one dot, so rpartition would treat ``stack.inputs[0]`` as the node.
        """
        node, _, attr = plug.partition(".")
        return node, attr

    def objExists(self, plug):
        if "." not in plug:
            return plug in self.nodes
        node, attr = self._split(plug)
        if node not in self.nodes:
            return False
        kind = self.nodes[node]
        # Model the plugs each node type actually exposes (verified on Maya 2025).
        # layeredTexture.inputs[N] is a compound with these children.
        if kind == "layeredTexture" and attr.startswith("inputs["):
            return attr.split(".")[-1] in {"color", "alpha", "blendMode", "isVisible"}
        known = {
            "file": {"fileTextureName", "useFrameExtension", "frameOffset", "colorSpace", "outColor"},
            "layeredTexture": {"inputs"},
            "blendColors": {"color1", "color2", "blender", "output"},
            "multiplyDivide": {"input1", "input2", "operation", "output"},
            "reverse": {"input", "output"},
            "plusMinusAverage": {"input3D", "output3D"},
            "luminance": {"value", "outValue"},
            "clamp": {"input", "output"},
            "setRange": {"value", "outValue"},
            "network": set(),
        }.get(kind, set())
        base = attr.split("[")[0]
        return base in known or attr in known

    def nodeType(self, node):
        # Accept a plug as well as a bare node name.
        return self.nodes.get(node.split(".")[0], "unknown")

    def getAttr(self, plug, **kwargs):
        if kwargs.get("size"):
            return 0  # Maya really does report 0 for a populated array
        return self.nodes.get("_attrs", {}).get(plug)

    def setAttr(self, plug, value=None, **_kwargs):
        self.calls.append(("setAttr", plug, value))
        self.nodes.setdefault("_attrs", {})[plug] = value

    def connectAttr(self, source, destination, **_kwargs):
        self.calls.append(("connectAttr", source, destination))
        if self.listConnections(destination, source=True, destination=False):
            raise RuntimeError("already connected")
        self.connections[destination] = source

    def disconnectAttr(self, source, destination):
        self.calls.append(("disconnectAttr", source, destination))
        self.connections.pop(destination, None)

    def _inputs_matching(self, node, attr):
        """Connections whose destination is under ``node.attr``.

        ``attr`` may name the whole array (``inputs``) or one element
        (``inputs[0]``); only the requested scope counts.
        """
        # A bare array name must still match its elements: inputs -> inputs[N].
        head = attr if attr.endswith("]") else attr + "["
        prefix = "{}.{}".format(node, head)
        return [
            (dest, src)
            for dest, src in sorted(self.connections.items())
            if dest.startswith(prefix) and ".color" in dest
        ]

    def listConnections(self, plug, **kwargs):
        node, _, attr = plug.rpartition(".")
        if attr.split("[")[0] == "inputs":
            matches = self._inputs_matching(node, attr)
            if kwargs.get("plugs"):
                # Real Maya returns the SOURCE plug, not the destination element.
                return [src for _dest, src in matches]
            return [src.split(".")[0] for _dest, src in matches]
        src = self.connections.get(plug)
        if kwargs.get("plugs"):
            return [src] if src else []
        return [src.split(".")[0]] if src else []


# ---------------------------------------------------------------------------
# Image readers
# ---------------------------------------------------------------------------


def test_create_image_reader_sets_the_path():
    cmds = _FakeCmds()

    result = create_image_reader(cmds, file_path="/shots/beauty.####.exr", name="bud")

    assert result["node"] == "bud"
    assert result["file_path"] == "/shots/beauty.####.exr"


def test_create_image_reader_can_enable_frame_extension():
    cmds = _FakeCmds()

    result = create_image_reader(cmds, file_path="/s/b.####.exr", use_frame_extension=True, frame_offset=1001)

    assert result["use_frame_extension"] is True
    assert result["frame_offset"] == 1001
    assert ("setAttr", "file1.useFrameExtension", True) in cmds.calls


def test_create_image_reader_requires_a_path():
    with pytest.raises(CompositingContractError, match="file_path"):
        create_image_reader(_FakeCmds(), file_path=" ")


def test_create_image_reader_sets_color_space_when_supported():
    cmds = _FakeCmds()

    result = create_image_reader(cmds, file_path="/s/b.exr", color_space="ACEScg")

    assert result["color_space"] == "ACEScg"


# ---------------------------------------------------------------------------
# Layer stacks
# ---------------------------------------------------------------------------


def _stack_with_two(cmds):
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]
    stack = create_layer_stack(cmds, name="stack")["node"]
    add_layer(cmds, stack, a, blend_mode="Over")
    add_layer(cmds, stack, b, blend_mode="Multiply", opacity=0.5)
    return stack, a, b


def test_create_layer_stack_makes_an_empty_stack():
    result = create_layer_stack(_FakeCmds(), name="stack")

    assert result["node"] == "stack"
    assert result["node_type"] == "layeredTexture"
    assert result["layers"] == 0


def test_add_layer_uses_distinct_indices():
    """Counting connections must not collapse every layer onto index 0."""
    cmds = _FakeCmds()
    stack, _a, _b = _stack_with_two(cmds)

    layers = list_layers(cmds, stack)["layers"]

    assert [item["index"] for item in layers] == [0, 1]


def test_add_layer_reports_mode_and_opacity():
    cmds = _FakeCmds()
    stack, _a, _b = _stack_with_two(cmds)

    layers = {item["index"]: item for item in list_layers(cmds, stack)["layers"]}

    assert layers[0]["blend_mode"] == "Over"
    assert layers[1]["blend_mode"] == "Multiply"
    assert layers[1]["opacity"] == 0.5


def test_add_layer_reuses_a_hole_left_by_a_removal():
    cmds = _FakeCmds()
    stack, a, b = _stack_with_two(cmds)
    remove_layer(cmds, stack, 0)

    result = add_layer(cmds, stack, a, blend_mode="Add")

    assert result["index"] == 0
    assert sorted(item["index"] for item in list_layers(cmds, stack)["layers"]) == [0, 1]


def test_add_layer_rejects_a_non_stack():
    cmds = _FakeCmds()
    reader = create_image_reader(cmds, file_path="/s/a.exr")["node"]

    with pytest.raises(CompositingContractError, match="expected a layeredTexture"):
        add_layer(cmds, reader, reader)


def test_add_layer_rejects_a_missing_source():
    cmds = _FakeCmds()
    stack = create_layer_stack(cmds)["node"]

    with pytest.raises(CompositingContractError, match="Node does not exist"):
        add_layer(cmds, stack, "ghost")


def test_add_layer_rejects_an_unknown_blend_mode():
    cmds = _FakeCmds()
    stack, a, _b = _stack_with_two(cmds)

    with pytest.raises(CompositingContractError, match="Unknown blend mode"):
        add_layer(cmds, stack, a, blend_mode="NotAMode")


def test_remove_layer_disconnects_without_deleting_the_source():
    cmds = _FakeCmds()
    stack, a, _b = _stack_with_two(cmds)

    result = remove_layer(cmds, stack, 0)

    assert result["source"] == a
    assert cmds.objExists(a)
    assert 0 not in [item["index"] for item in list_layers(cmds, stack)["layers"]]


def test_remove_layer_rejects_an_empty_slot():
    cmds = _FakeCmds()
    stack = create_layer_stack(cmds)["node"]

    with pytest.raises(CompositingContractError, match="empty"):
        remove_layer(cmds, stack, 0)


def test_remove_layer_rejects_a_negative_index():
    cmds = _FakeCmds()
    stack, _a, _b = _stack_with_two(cmds)

    with pytest.raises(CompositingContractError, match="index must be >= 0"):
        remove_layer(cmds, stack, -1)


def test_remove_layer_rejects_a_non_integer_index():
    cmds = _FakeCmds()
    stack, _a, _b = _stack_with_two(cmds)

    with pytest.raises(CompositingContractError, match="index must be an integer"):
        remove_layer(cmds, stack, "zero")


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


def test_merge_blend_uses_blend_colors_with_two_sources():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]

    result = merge_layers(cmds, [a, b], operation="blend", blend_amount=0.25)

    assert result["node_type"] == "blendColors"
    assert result["blend_amount"] == 0.25


def test_merge_blend_rejects_more_than_two_sources():
    cmds = _FakeCmds()
    nodes = [create_image_reader(cmds, file_path="/s/{}.exr".format(i), name=n)["node"] for i, n in enumerate("abc")]

    with pytest.raises(CompositingContractError, match="exactly two sources"):
        merge_layers(cmds, nodes, operation="blend")


def test_merge_layered_operation_stacks_sources():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]

    result = merge_layers(cmds, [a, b], operation="multiply")

    assert result["node_type"] == "layeredTexture"
    assert result["blend_mode"] == "Multiply"


def test_merge_requires_two_sources():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]

    with pytest.raises(CompositingContractError, match="at least two sources"):
        merge_layers(cmds, [a], operation="over")


def test_merge_rejects_an_unknown_operation():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]

    with pytest.raises(CompositingContractError, match="Unknown merge operation"):
        merge_layers(cmds, [a, b], operation="screen")


# ---------------------------------------------------------------------------
# Utility nodes
# ---------------------------------------------------------------------------


def test_create_comp_node_sets_multiply_divide_operation():
    cmds = _FakeCmds()

    result = create_comp_node(cmds, "multiplyDivide", operation="divide")

    assert result["node_type"] == "multiplyDivide"
    assert result["operation"] == "divide"
    assert ("setAttr", "multiplyDivide1.operation", MULTIPLY_DIVIDE_OPS["divide"]) in cmds.calls


def test_create_comp_node_rejects_an_unsupported_type():
    """`grade` returns an unknown node under Maya, so it is deliberately excluded."""
    with pytest.raises(CompositingContractError, match="Unsupported comp node"):
        create_comp_node(_FakeCmds(), "grade")


def test_create_comp_node_rejects_an_unknown_operation():
    with pytest.raises(CompositingContractError, match="Unknown operation"):
        create_comp_node(_FakeCmds(), "multiplyDivide", operation="modulo")


def test_create_comp_node_rejects_operation_on_a_node_without_one():
    with pytest.raises(CompositingContractError, match="only applies to multiplyDivide"):
        create_comp_node(_FakeCmds(), "reverse", operation="divide")


def test_connect_comp_uses_input1_then_input2():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]
    md = create_comp_node(cmds, "multiplyDivide", name="md")["node"]

    first = connect_comp(cmds, a, md)
    second = connect_comp(cmds, b, md)

    assert first["destination"] == "md.input1"
    assert second["destination"] == "md.input2"


def test_connect_comp_uses_the_node_specific_input_plug():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    reverse = create_comp_node(cmds, "reverse", name="rv")["node"]

    result = connect_comp(cmds, a, reverse)

    assert result["destination"] == "rv.input"


def test_connect_comp_rejects_a_file_node_as_destination():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]

    with pytest.raises(CompositingContractError, match="no colour input"):
        connect_comp(cmds, a, b)


def test_connect_comp_rejects_an_unsupported_destination_type():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    other = cmds.createNode("network", name="net")

    with pytest.raises(CompositingContractError, match="Unsupported destination type"):
        connect_comp(cmds, a, other)


def test_connect_comp_rejects_a_missing_source_plug():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    md = create_comp_node(cmds, "multiplyDivide", name="md")["node"]

    with pytest.raises(CompositingContractError, match="Source plug does not exist"):
        connect_comp(cmds, a, md, source_attr="notAPlug")


def test_connect_comp_reports_when_all_inputs_are_taken():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]
    c = create_image_reader(cmds, file_path="/s/c.exr", name="c")["node"]
    md = create_comp_node(cmds, "multiplyDivide", name="md")["node"]
    connect_comp(cmds, a, md)
    connect_comp(cmds, b, md)

    with pytest.raises(CompositingContractError, match="no free input"):
        connect_comp(cmds, c, md)


def test_constants_cover_the_supported_surface():
    assert "Over" in BLEND_MODES
    assert set(MERGE_OPS) == {"blend", "over", "add", "multiply", "subtract", "difference"}
    assert set(MULTIPLY_DIVIDE_OPS) == {"none", "multiply", "divide", "power"}
    assert "grade" not in UTILITY_NODES
    assert INPUT_PLUGS["multiplyDivide"] == ("input1", "input2")


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


def _call(script, cmds, **kwargs):
    return load_and_call("maya-compositing/scripts/{}.py".format(script), cmds, "main", **kwargs)


def test_skill_create_image_reader_succeeds():
    result = _call("create_image_reader", _FakeCmds(), file_path="/s/b.####.exr", use_frame_extension=True)

    assert result["success"] is True, result
    assert result["context"]["file_path"] == "/s/b.####.exr"


def test_skill_create_image_reader_requires_a_path():
    result = _call("create_image_reader", _FakeCmds(), file_path="")

    assert result["success"] is False


def test_skill_create_layer_stack_succeeds():
    result = _call("create_layer_stack", _FakeCmds(), name="stack")

    assert result["success"] is True, result
    assert result["context"]["node"] == "stack"


def test_skill_add_comp_layer_succeeds():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    stack = create_layer_stack(cmds, name="stack")["node"]

    result = _call("add_comp_layer", cmds, stack=stack, source=a, blend_mode="Over")

    assert result["success"] is True, result
    assert result["context"]["index"] == 0


def test_skill_add_comp_layer_rejects_a_bad_blend_mode_and_lists_them():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    stack = create_layer_stack(cmds, name="stack")["node"]

    result = _call("add_comp_layer", cmds, stack=stack, source=a, blend_mode="Nope")

    assert result["success"] is False
    assert "Over" in " ".join(result["context"].get("possible_solutions") or [])


def test_skill_list_comp_layers_reports_count():
    cmds = _FakeCmds()
    _stack, _a, _b = _stack_with_two(cmds)

    result = _call("list_comp_layers", cmds, stack="stack")

    assert result["success"] is True, result
    assert result["context"]["count"] == 2


def test_skill_list_comp_layers_rejects_a_missing_stack():
    result = _call("list_comp_layers", _FakeCmds(), stack="ghost")

    assert result["success"] is False


def test_skill_remove_comp_layer_succeeds():
    cmds = _FakeCmds()
    _stack, _a, _b = _stack_with_two(cmds)

    result = _call("remove_comp_layer", cmds, stack="stack", index=0)

    assert result["success"] is True, result
    assert result["context"]["removed_index"] == 0


def test_skill_remove_comp_layer_rejects_an_empty_slot():
    cmds = _FakeCmds()
    create_layer_stack(cmds, name="stack")

    result = _call("remove_comp_layer", cmds, stack="stack", index=3)

    assert result["success"] is False


def test_skill_merge_comp_layers_succeeds():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]

    result = _call("merge_comp_layers", cmds, sources=[a, b], operation="multiply")

    assert result["success"] is True, result
    assert result["context"]["node_type"] == "layeredTexture"


def test_skill_merge_comp_layers_rejects_a_bad_operation():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]

    result = _call("merge_comp_layers", cmds, sources=[a, b], operation="screen")

    assert result["success"] is False


def test_skill_create_comp_node_succeeds():
    result = _call("create_comp_node", _FakeCmds(), node_type="luminance", name="lum")

    assert result["success"] is True, result
    assert result["context"]["node"] == "lum"


def test_skill_create_comp_node_rejects_an_unsupported_type():
    result = _call("create_comp_node", _FakeCmds(), node_type="grade")

    assert result["success"] is False


def test_skill_connect_comp_nodes_succeeds():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    md = create_comp_node(cmds, "multiplyDivide", name="md")["node"]

    result = _call("connect_comp_nodes", cmds, source=a, destination=md)

    assert result["success"] is True, result
    assert result["context"]["destination"] == "md.input1"


def test_skill_connect_comp_nodes_rejects_a_file_destination():
    cmds = _FakeCmds()
    a = create_image_reader(cmds, file_path="/s/a.exr", name="a")["node"]
    b = create_image_reader(cmds, file_path="/s/b.exr", name="b")["node"]

    result = _call("connect_comp_nodes", cmds, source=a, destination=b)

    assert result["success"] is False
