"""Unit tests for the render setup / AOV contract and the maya-render-setup skill.

Rejection branches are covered deliberately: batch 1's review findings all came
from only testing the happy path.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from conftest import load_and_call

from dcc_mcp_maya import render_setup as render_setup_mod
from dcc_mcp_maya.render_setup import (
    AOV_TYPE_MAX,
    AOV_TYPE_MIN,
    AOV_TYPES,
    OVERRIDE_TYPES,
    RENDER_SETUP_MODULE,
    RenderSetupContractError,
    add_aov,
    build_output_paths,
    create_collection,
    create_override,
    create_render_layer,
    ensure_arnold,
    list_aovs,
    list_legacy_render_layers,
    list_render_layers,
    remove_aov,
    resolve_aov_type,
    set_aov_enabled,
    set_collection_members,
    switch_legacy_render_layer,
    switch_render_layer,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeCollection:
    def __init__(self, name):
        self._name = name
        self._selector = _FakeSelector()
        self.overrides = []

    def name(self):
        return self._name

    def getSelector(self):
        return self._selector

    def createAbsoluteOverride(self, node, attr):
        return self._new_override(node, attr, "absolute")

    def createRelativeOverride(self, node, attr):
        return self._new_override(node, attr, "relative")

    def createConnectionOverride(self, attr, source):  # noqa: ARG002 - source is Maya-side
        return self._new_override(None, attr, "connection")

    def _new_override(self, node, attr, kind):
        override = _FakeOverride(node, attr, kind)
        self.overrides.append(override)
        return override


class _FakeOverride:
    def __init__(self, node, attr, kind):
        self.node = node
        self.attr = attr
        self.kind = kind
        self._value = None

    def setAttrValue(self, value):
        self._value = value

    def name(self):
        return self.attr


class _FakeSelector:
    def __init__(self):
        self.static = []
        self.pattern_value = None

    def setStaticSelection(self, nodes):
        self.static = list(nodes)
        self.pattern_value = None

    def setPattern(self, pattern):
        self.pattern_value = pattern
        self.static = []


class _FakeLayer:
    def __init__(self, name, renderable=True, visible=False):
        self._name = name
        self._renderable = renderable
        self._visible = visible
        self.collections = []

    def name(self):
        return self._name

    def isRenderable(self):
        return self._renderable

    def setRenderable(self, value):
        self._renderable = bool(value)

    def isVisible(self):
        return self._visible

    def makeVisible(self):
        self._visible = True

    def getCollections(self):
        return list(self.collections)

    def createCollection(self, name):
        collection = _FakeCollection(name)
        self.collections.append(collection)
        return collection


class _FakeRenderSetup:
    """Stand-in for the renderSetup singleton."""

    def __init__(self):
        self.layers = []
        self.visible = None
        self.default = _FakeLayer("defaultRenderLayer")

    def getRenderLayers(self):
        return list(self.layers)

    def getDefaultRenderLayer(self):
        return self.default

    def getVisibleRenderLayer(self):
        return self.visible

    def createRenderLayer(self, name):
        layer = _FakeLayer(name)
        self.layers.append(layer)
        return layer

    def switchToLayer(self, layer):
        self.visible = layer
        for item in self.layers + [self.default]:
            item._visible = item is layer


class _FakeCmds:
    """Minimal ``maya.cmds`` stand-in for the AOV and legacy layer paths."""

    def __init__(self, arnold_loaded=True, options_exists=False, aovs=None):
        self.arnold_loaded = arnold_loaded
        self.options_exists = options_exists
        self.nodes = {}
        self.attrs = {}
        if options_exists:
            self.nodes["defaultArnoldRenderOptions"] = "aiOptions"
        self.connections = list(aovs or [])
        self.aov_slots = dict(enumerate(self.connections))
        self.deleted = []
        self.calls = []
        self.legacy_layers = ["defaultRenderLayer"]
        self.legacy_current = "defaultRenderLayer"

    # -- plugins / nodes ----------------------------------------------------
    def pluginInfo(self, plugin, **kwargs):
        if kwargs.get("loaded"):
            return self.arnold_loaded
        return None

    def loadPlugin(self, plugin, **_kwargs):
        self.calls.append(("loadPlugin", plugin))
        self.arnold_loaded = True
        return [plugin]

    def objExists(self, node):
        if "." in node:
            parent, _, attr = node.rpartition(".")
            if parent == "defaultArnoldRenderOptions" and attr == "aovList":
                return self.options_exists
            return attr in self.attrs.get(parent, {})
        return node in self.nodes or node in self.legacy_layers

    def createNode(self, node_type, name=None):
        self.calls.append(("createNode", node_type, name))
        node = name or "{}1".format(node_type)
        self.nodes[node] = node_type
        # Attribute values live in a side dict keyed off the node name.
        self.attrs.setdefault(node, {})
        if node_type == "aiOptions":
            self.options_exists = True
        return node

    def ls(self, **kwargs):
        if kwargs.get("type") == "renderLayer":
            return list(self.legacy_layers)
        return []

    def delete(self, node):
        self.deleted.append(node)
        self.connections = [item for item in self.connections if item != node]
        self.nodes.pop(node, None)

    # -- attributes ---------------------------------------------------------
    def setAttr(self, plug, value=None, **_kwargs):
        self.calls.append(("setAttr", plug, value))
        node, _, attr = plug.rpartition(".")
        self.attrs.setdefault(node, {})
        self.attrs[node][attr] = value

    def getAttr(self, plug, **kwargs):
        if kwargs.get("size"):
            return 0  # Maya really does report 0 for a populated array
        node, _, attr = plug.rpartition(".")
        if attr == "type" and attr not in self.attrs.get(node, {}):
            # aiAOV.type defaults to rgba (6) until explicitly set.
            return 6
        return self.attrs.get(node, {}).get(attr)

    def listConnections(self, plug, **kwargs):
        if plug.endswith(".aovList"):
            if kwargs.get("plugs"):
                # Sparse array: report the real element index for each entry.
                # Maya returns the destination plug, e.g. "...aovList[0]".
                return [
                    "{}[{}]".format(plug, index)
                    for index in sorted(self.aov_slots)
                    if self.aov_slots.get(index) in self.connections
                ]
            return list(self.connections)
        if "[" in plug:
            index = int(plug.rsplit("[", 1)[1].rstrip("]"))
            node = self.aov_slots.get(index)
            if node is None or node not in self.connections:
                return []
            return [node]
        return []

    def connectAttr(self, source, destination, **_kwargs):
        self.calls.append(("connectAttr", source, destination))
        node = source.rpartition(".")[0]
        index = int(destination.rsplit("[", 1)[1].rstrip("]"))
        if self.aov_slots.get(index) is not None and self.aov_slots[index] != node:
            raise RuntimeError("slot {} already occupied".format(index))
        self.aov_slots[index] = node
        if node not in self.connections:
            self.connections.append(node)

    def disconnectAttr(self, source, destination):
        self.calls.append(("disconnectAttr", source))
        node = source.rpartition(".")[0]
        index = int(destination.rsplit("[", 1)[1].rstrip("]"))
        if self.aov_slots.get(index) == node:
            # Sparse array: disconnecting frees the slot, it does not renumber.
            del self.aov_slots[index]
        self.connections = [item for item in self.connections if item != node]

    def editRenderLayerGlobals(self, **kwargs):
        if kwargs.get("query"):
            return self.legacy_current
        self.legacy_current = kwargs.get("currentRenderLayer")
        return True


# ---------------------------------------------------------------------------
# renderSetup layers
# ---------------------------------------------------------------------------


@contextmanager
def _patch_render_setup(setup):
    """Seed ``sys.modules`` so ``load_render_setup()`` resolves to ``setup``."""
    fake_module = MagicMock()
    fake_module.instance.return_value = setup
    with patch.dict(sys.modules, {RENDER_SETUP_MODULE: fake_module}):
        yield


def _call_skill(script, cmds=None, setup=None, **kwargs):
    """Load and call a skill script with renderSetup and/or cmds faked."""
    rel = "maya-render-setup/scripts/{}.py".format(script)
    fake_cmds = cmds if cmds is not None else MagicMock()
    if setup is not None:
        with _patch_render_setup(setup):
            return load_and_call(rel, fake_cmds, "main", **kwargs)
    return load_and_call(rel, fake_cmds, "main", **kwargs)


def test_create_render_layer_sets_renderable_and_activation():
    setup = _FakeRenderSetup()

    result = create_render_layer(setup, name="beauty", renderable=True, activate=True)

    assert result["created"] == "beauty"
    assert result["layer"]["renderable"] is True
    assert result["layer"]["visible"] is True


def test_create_render_layer_rejects_duplicate_name():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    with pytest.raises(RenderSetupContractError, match="already exists"):
        create_render_layer(setup, name="beauty")


def test_create_render_layer_rejects_empty_name():
    with pytest.raises(RenderSetupContractError, match="must be a non-empty name"):
        create_render_layer(_FakeRenderSetup(), name=" ")


def test_list_render_layers_reports_default_and_visible():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")
    switch_render_layer(setup, "beauty")

    result = list_render_layers(setup)

    assert [item["name"] for item in result["layers"]] == ["beauty"]
    assert result["default_layer"] == "defaultRenderLayer"
    assert result["visible_layer"] == "beauty"


def test_list_render_layers_can_hide_default():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    result = list_render_layers(setup, include_default=False)

    assert [item["name"] for item in result["layers"]] == ["beauty"]


def test_switch_render_layer_updates_visible_layer():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    result = switch_render_layer(setup, "beauty")

    assert result["visible_layer"] == "beauty"
    assert setup.getVisibleRenderLayer().name() == "beauty"


def test_switch_render_layer_can_return_to_default():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    result = switch_render_layer(setup, "defaultRenderLayer")

    assert result["layer"] == "defaultRenderLayer"


def test_switch_render_layer_rejects_unknown_layer_and_lists_known():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    with pytest.raises(RenderSetupContractError, match="No render layer named ghost"):
        switch_render_layer(setup, "ghost")


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------


def _layer_with(setup, name="beauty"):
    create_render_layer(setup, name=name)
    return setup


def test_create_collection_with_static_members():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    result = create_collection(setup, layer="beauty", name="hero_set", members=["hero", "sidekick"])

    assert result["selector_type"] == "static"
    assert result["requested"] == ["hero", "sidekick"]
    layer = setup.layers[0]
    assert layer.collections[0].getSelector().static == ["hero", "sidekick"]


def test_create_collection_with_pattern():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    result = create_collection(setup, layer="beauty", name="hero_set", pattern="hero*")

    assert result["selector_type"] == "pattern"
    assert result["pattern"] == "hero*"
    assert setup.layers[0].collections[0].getSelector().pattern_value == "hero*"


def test_create_collection_rejects_members_and_pattern_together():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    with pytest.raises(RenderSetupContractError, match="not both"):
        create_collection(setup, layer="beauty", name="c", members=["hero"], pattern="hero*")


def test_create_collection_requires_content():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    with pytest.raises(RenderSetupContractError, match="members or a pattern"):
        create_collection(setup, layer="beauty", name="c")


def test_create_collection_rejects_duplicate():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")
    create_collection(setup, layer="beauty", name="hero_set", members=["hero"])

    with pytest.raises(RenderSetupContractError, match="already has a collection"):
        create_collection(setup, layer="beauty", name="hero_set", members=["hero"])


def test_create_collection_rejects_unknown_layer():
    with pytest.raises(RenderSetupContractError, match="No render layer named ghost"):
        create_collection(_FakeRenderSetup(), layer="ghost", name="c", members=["hero"])


def test_set_collection_members_replaces_contents():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")
    create_collection(setup, layer="beauty", name="hero_set", members=["hero"])

    result = set_collection_members(setup, layer="beauty", collection="hero_set", members=["sidekick"])

    assert result["requested"] == ["sidekick"]
    assert setup.layers[0].collections[0].getSelector().static == ["sidekick"]


def test_set_collection_members_rejects_empty_members():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")
    create_collection(setup, layer="beauty", name="hero_set", members=["hero"])

    with pytest.raises(RenderSetupContractError, match="at least one node"):
        set_collection_members(setup, layer="beauty", collection="hero_set", members=[])


def test_set_collection_members_rejects_unknown_collection():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")

    with pytest.raises(RenderSetupContractError, match="has no collection named ghost"):
        set_collection_members(setup, layer="beauty", collection="ghost", members=["hero"])


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------


def _setup_with_collection():
    setup = _FakeRenderSetup()
    create_render_layer(setup, name="beauty")
    create_collection(setup, layer="beauty", name="hero_set", members=["hero"])
    return setup


def test_create_absolute_override_sets_value():
    setup = _setup_with_collection()

    result = create_override(setup, layer="beauty", collection="hero_set", attribute="hero.visibility", value=False)

    assert result["override_type"] == "absolute"
    assert result["override"] == "visibility"
    assert setup.layers[0].collections[0].overrides[0]._value is False


def test_create_relative_override():
    setup = _setup_with_collection()

    result = create_override(
        setup,
        layer="beauty",
        collection="hero_set",
        attribute="hero.visibility",
        value=0.5,
        override_type="relative",
    )

    assert result["override_type"] == "relative"
    assert setup.layers[0].collections[0].overrides[0]._value == 0.5


def test_create_connection_override_does_not_need_a_value():
    setup = _setup_with_collection()

    result = create_override(
        setup,
        layer="beauty",
        collection="hero_set",
        attribute="hero.visibility",
        value="somePlug",
        override_type="connection",
    )

    assert result["override_type"] == "connection"


def test_create_override_rejects_unknown_type():
    setup = _setup_with_collection()

    with pytest.raises(RenderSetupContractError, match="override_type must be one of"):
        create_override(
            setup, layer="beauty", collection="hero_set", attribute="hero.visibility", value=1, override_type="magic"
        )


def test_create_override_requires_a_value():
    setup = _setup_with_collection()

    with pytest.raises(RenderSetupContractError, match="value is required"):
        create_override(setup, layer="beauty", collection="hero_set", attribute="hero.visibility")


def test_create_override_rejects_unknown_collection():
    setup = _setup_with_collection()

    with pytest.raises(RenderSetupContractError, match="has no collection named ghost"):
        create_override(setup, layer="beauty", collection="ghost", attribute="a.b", value=1)


def test_override_types_match_the_maya_surface():
    assert set(OVERRIDE_TYPES) == {"absolute", "relative", "connection"}


# ---------------------------------------------------------------------------
# Legacy render layers
# ---------------------------------------------------------------------------


def test_list_legacy_render_layers_reports_current():
    cmds = _FakeCmds()
    cmds.legacy_layers = ["defaultRenderLayer", "legacy_beauty"]

    result = list_legacy_render_layers(cmds)

    assert result["count"] == 2
    assert result["current"] == "defaultRenderLayer"


def test_switch_legacy_render_layer_reports_when_it_did_not_apply():
    """Maya silently ignores legacy switches in batch; the tool must say so."""
    cmds = _FakeCmds()
    cmds.legacy_layers = ["defaultRenderLayer", "legacy_beauty"]

    def _ignored(**kwargs):
        if kwargs.get("query"):
            return "defaultRenderLayer"
        return True  # accept the set, but readback never changes

    cmds.editRenderLayerGlobals = _ignored

    result = switch_legacy_render_layer(cmds, "legacy_beauty")

    assert result["requested"] == "legacy_beauty"
    assert result["applied"] is False


def test_switch_legacy_render_layer_rejects_unknown_layer():
    cmds = _FakeCmds()

    with pytest.raises(RenderSetupContractError, match="No legacy render layer named ghost"):
        switch_legacy_render_layer(cmds, "ghost")


def test_switch_legacy_render_layer_rejects_empty_name():
    with pytest.raises(RenderSetupContractError, match="must be a non-empty name"):
        switch_legacy_render_layer(_FakeCmds(), " ")


# ---------------------------------------------------------------------------
# AOVs
# ---------------------------------------------------------------------------


def test_ensure_arnold_creates_options_node_when_missing():
    cmds = _FakeCmds(arnold_loaded=True, options_exists=False)

    result = ensure_arnold(cmds)

    assert result["options_node"] == "defaultArnoldRenderOptions"
    assert ("createNode", "aiOptions", "defaultArnoldRenderOptions") in cmds.calls


def test_ensure_arnold_does_not_recreate_existing_options():
    cmds = _FakeCmds(arnold_loaded=True)
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"

    ensure_arnold(cmds)

    assert not any(call[0] == "createNode" and call[1] == "aiOptions" for call in cmds.calls)


def test_ensure_arnold_fails_closed_when_plugin_is_unavailable():
    cmds = _FakeCmds(arnold_loaded=False)

    def _boom(plugin, **_kwargs):
        raise RuntimeError("plug-in not found")

    cmds.loadPlugin = _boom

    with pytest.raises(RenderSetupContractError, match="could not be loaded"):
        ensure_arnold(cmds)


def test_add_aov_wires_into_next_free_index():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"

    result = add_aov(cmds, name="beauty", aov_type="rgba")

    assert result["index"] == 0
    assert result["aov"]["name"] == "beauty"
    assert result["aov"]["type"] == AOV_TYPES["rgba"]


def test_add_aov_uses_listconnections_for_the_index_not_getattr_size():
    """`aovList` reports size 0 even when populated; the count must come from
    listConnections or the second AOV overwrites the first."""
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"
    add_aov(cmds, name="beauty")

    second = add_aov(cmds, name="depth", aov_type="float")

    assert second["index"] == 1
    assert cmds.connections == ["aiAOV_beauty", "aiAOV_depth"]


def test_add_aov_rejects_duplicate_name():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"
    add_aov(cmds, name="beauty")

    with pytest.raises(RenderSetupContractError, match="already exists"):
        add_aov(cmds, name="beauty")


def test_add_aov_rejects_empty_name():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"

    with pytest.raises(RenderSetupContractError, match="must be a non-empty name"):
        add_aov(cmds, name=" ")


def test_resolve_aov_type_accepts_names_and_numbers():
    assert resolve_aov_type("rgba") == 6
    assert resolve_aov_type("RGBA") == 6
    assert resolve_aov_type(6) == 6
    assert resolve_aov_type(None) == AOV_TYPES["rgba"]


def test_resolve_aov_type_rejects_unknown_name():
    with pytest.raises(RenderSetupContractError, match="Unknown AOV type"):
        resolve_aov_type("notatype")


def test_resolve_aov_type_rejects_out_of_range_number():
    with pytest.raises(RenderSetupContractError, match="outside the supported range"):
        resolve_aov_type(999)


def test_resolve_aov_type_accepts_range_boundaries():
    assert resolve_aov_type(AOV_TYPE_MIN) == AOV_TYPE_MIN
    assert resolve_aov_type(AOV_TYPE_MAX) == AOV_TYPE_MAX


def test_list_aovs_reports_each_entry():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"
    add_aov(cmds, name="beauty")
    add_aov(cmds, name="depth", aov_type="float")

    result = list_aovs(cmds)

    assert result["count"] == 2
    assert [item["name"] for item in result["aovs"]] == ["beauty", "depth"]


def test_set_aov_enabled_toggles_without_disconnecting():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"
    add_aov(cmds, name="beauty")

    result = set_aov_enabled(cmds, "beauty", False)

    assert result["enabled"] is False
    assert cmds.connections == ["aiAOV_beauty"]


def test_set_aov_enabled_rejects_unknown_aov_and_lists_current():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"
    add_aov(cmds, name="beauty")

    with pytest.raises(RenderSetupContractError, match="No AOV named ghost"):
        set_aov_enabled(cmds, "ghost", True)


def test_add_aov_reuses_a_hole_left_by_a_removal():
    """aovList is sparse: a removed index leaves a hole that must be reused.

    Counting connections to pick the index collides with a live element, and
    connectAttr(force=True) then silently replaces an existing AOV.
    """
    cmds = _FakeCmds(options_exists=True)
    add_aov(cmds, name="a")
    add_aov(cmds, name="b")
    add_aov(cmds, name="c")
    remove_aov(cmds, "b")  # frees index 1, leaving {0, 2}

    result = add_aov(cmds, name="d")

    assert result["index"] == 1
    # Slots, not insertion order, express the sparse array layout.
    assert cmds.aov_slots == {0: "aiAOV_a", 1: "aiAOV_d", 2: "aiAOV_c"}


def test_add_aov_does_not_replace_a_live_aov():
    cmds = _FakeCmds(options_exists=True)
    add_aov(cmds, name="a")
    add_aov(cmds, name="b")
    add_aov(cmds, name="c")
    remove_aov(cmds, "b")
    add_aov(cmds, name="d")

    names = {record["name"] for record in list_aovs(cmds)["aovs"]}
    assert names == {"a", "c", "d"}, "a live AOV was replaced"
    assert cmds.aov_slots[2] == "aiAOV_c", "index 2 must still hold the original AOV"


def test_remove_aov_deletes_only_the_requested_node():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"
    add_aov(cmds, name="beauty")
    add_aov(cmds, name="depth", aov_type="float")

    result = remove_aov(cmds, "depth")

    assert result["removed"]["name"] == "depth"
    assert cmds.deleted == ["aiAOV_depth"]
    assert cmds.connections == ["aiAOV_beauty"]
    assert result["remaining"] == 1


def test_remove_aov_rejects_unknown_aov():
    cmds = _FakeCmds()
    cmds.nodes["defaultArnoldRenderOptions"] = "aiOptions"
    add_aov(cmds, name="beauty")

    with pytest.raises(RenderSetupContractError, match="No AOV named ghost"):
        remove_aov(cmds, "ghost")


def test_aov_types_are_in_the_supported_range():
    assert all(AOV_TYPE_MIN <= value <= AOV_TYPE_MAX for value in AOV_TYPES.values())


# ---------------------------------------------------------------------------
# Precomp output planning (pure - no Maya)
# ---------------------------------------------------------------------------


def test_build_output_paths_composes_layer_and_aov_folders():
    result = build_output_paths(
        "/out",
        layers=["beauty", "char"],
        aovs=["depth"],
        file_name="shot",
        start_frame=1001,
        end_frame=1100,
    )

    assert result["count"] == 2
    first = result["outputs"][0]
    assert first["layer"] == "beauty"
    assert first["aov"] == "depth"
    assert first["pattern"] == "shot_beauty_depth.####.exr"
    assert first["frame_range"] == [1001, 1100]
    assert first["frame_count"] == 100


def test_build_output_paths_can_flatten_folders():
    result = build_output_paths(
        "/out",
        layers=["beauty"],
        aovs=["depth"],
        separate_aov_folders=False,
        separate_layer_folders=False,
    )

    assert result["outputs"][0]["directory"] == "/out"


def test_build_output_paths_without_layers_or_aovs_yields_one_output():
    result = build_output_paths("/out")

    assert result["count"] == 1
    assert result["outputs"][0]["layer"] is None
    assert result["outputs"][0]["aov"] is None


def test_build_output_paths_rejects_missing_directory():
    with pytest.raises(RenderSetupContractError, match="directory is required"):
        build_output_paths(" ")


def test_build_output_paths_rejects_bad_padding():
    with pytest.raises(RenderSetupContractError, match="frame_padding must be"):
        build_output_paths("/out", frame_padding=0)


def test_build_output_paths_rejects_inverted_frame_range():
    with pytest.raises(RenderSetupContractError, match="end_frame .* must be >= start_frame"):
        build_output_paths("/out", start_frame=10, end_frame=1)


def test_build_output_paths_rejects_non_integer_frames():
    with pytest.raises(RenderSetupContractError, match="must be integers"):
        build_output_paths("/out", start_frame="a")


def test_build_output_paths_honours_padding_and_extension():
    result = build_output_paths("/out", frame_padding=3, extension=".png")

    assert result["outputs"][0]["pattern"].endswith(".###.png")


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


def test_skill_create_render_layer_returns_success():
    setup = _FakeRenderSetup()

    result = _call_skill("create_render_layer", setup=setup, name="beauty")

    assert result["success"] is True, result
    assert result["context"]["created"] == "beauty"


def test_skill_create_render_layer_rejects_duplicate():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")

    result = _call_skill("create_render_layer", setup=setup, name="beauty")

    assert result["success"] is False
    assert "already exists" in result["error"]


def test_skill_list_render_layers_reports_counts():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")

    result = _call_skill("list_render_layers", setup=setup)

    assert result["success"] is True, result
    assert result["context"]["count"] == 1


def test_skill_set_current_render_layer_switches_layer():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")

    result = _call_skill("set_current_render_layer", setup=setup, name="beauty")

    assert result["success"] is True, result
    assert result["context"]["visible_layer"] == "beauty"


def test_skill_set_current_render_layer_rejects_bad_system():
    result = _call_skill("set_current_render_layer", name="beauty", layer_system="nope")

    assert result["success"] is False
    assert "layer_system" in result["error"]


def test_skill_set_current_render_layer_rejects_unknown_layer():
    setup = _FakeRenderSetup()

    result = _call_skill("set_current_render_layer", setup=setup, name="ghost")

    assert result["success"] is False
    assert "No render layer named ghost" in result["error"]


def test_skill_legacy_switch_reports_when_it_did_not_apply():
    """A silent batch no-op must surface as an error, not a success."""
    cmds = _FakeCmds()
    cmds.legacy_layers = ["defaultRenderLayer", "legacy_beauty"]

    def _ignored(**kwargs):
        if kwargs.get("query"):
            return "defaultRenderLayer"
        return True

    cmds.editRenderLayerGlobals = _ignored

    result = _call_skill("set_current_render_layer", cmds=cmds, name="legacy_beauty", layer_system="legacy")

    assert result["success"] is False
    assert "did not take effect" in result["message"]


def test_skill_create_render_collection_requires_content():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")

    result = _call_skill("create_render_collection", setup=setup, layer="beauty", name="c")

    assert result["success"] is False


def test_skill_create_render_collection_accepts_members():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")

    result = _call_skill(
        "create_render_collection",
        setup=setup,
        layer="beauty",
        name="hero_set",
        members=["hero"],
    )

    assert result["success"] is True, result
    assert result["context"]["requested"] == ["hero"]


def test_skill_create_render_override_requires_a_value():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")
    _call_skill("create_render_collection", setup=setup, layer="beauty", name="hero_set", members=["hero"])

    result = _call_skill(
        "create_render_override", setup=setup, layer="beauty", collection="hero_set", attribute="hero.visibility"
    )

    assert result["success"] is False


def test_skill_create_render_override_sets_the_value():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")
    _call_skill("create_render_collection", setup=setup, layer="beauty", name="hero_set", members=["hero"])

    result = _call_skill(
        "create_render_override",
        setup=setup,
        layer="beauty",
        collection="hero_set",
        attribute="hero.visibility",
        value=False,
    )

    assert result["success"] is True, result
    assert result["context"]["override_type"] == "absolute"


def test_skill_create_render_override_rejects_unknown_type():
    setup = _FakeRenderSetup()
    _call_skill("create_render_layer", setup=setup, name="beauty")
    _call_skill("create_render_collection", setup=setup, layer="beauty", name="hero_set", members=["hero"])

    result = _call_skill(
        "create_render_override",
        setup=setup,
        layer="beauty",
        collection="hero_set",
        attribute="hero.visibility",
        value=1,
        override_type="magic",
    )

    assert result["success"] is False
    assert "absolute" in " ".join(result["context"].get("possible_solutions") or [])


def test_skill_plan_comp_outputs_needs_no_maya():
    result = _call_skill(
        "plan_comp_outputs",
        directory="/out",
        layers=["beauty"],
        aovs=["depth"],
        start_frame=1,
        end_frame=24,
    )

    assert result["success"] is True, result
    assert result["context"]["count"] == 1
    assert result["context"]["frame_range"] == [1, 24]


def test_skill_plan_comp_outputs_rejects_inverted_range():
    result = _call_skill("plan_comp_outputs", directory="/out", start_frame=24, end_frame=1)

    assert result["success"] is False


def test_skill_plan_comp_outputs_rejects_missing_directory():
    result = _call_skill("plan_comp_outputs")

    assert result["success"] is False


def _arnold_cmds():
    return _FakeCmds(options_exists=True)


def test_skill_add_aov_wires_the_aov():
    cmds = _arnold_cmds()

    result = _call_skill("add_aov", cmds=cmds, name="beauty")

    assert result["success"] is True, result
    assert result["context"]["index"] == 0


def test_skill_add_aov_fails_closed_when_arnold_is_missing():
    """A missing renderer must be an actionable error, never a silent no-op."""
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    cmds.loadPlugin.side_effect = RuntimeError("mtoa not found")

    result = _call_skill("add_aov", cmds=cmds, name="beauty")

    assert result["success"] is False
    assert "mtoa" in result["error"]


def test_skill_add_aov_rejects_bad_type_and_suggests_valid_ones():
    cmds = _arnold_cmds()

    result = _call_skill("add_aov", cmds=cmds, name="x", aov_type="notatype")

    assert result["success"] is False
    assert "rgba" in " ".join(result["context"].get("possible_solutions") or [])


def test_skill_list_aovs_reports_entries():
    cmds = _arnold_cmds()
    _call_skill("add_aov", cmds=cmds, name="beauty")

    result = _call_skill("list_aovs", cmds=cmds)

    assert result["success"] is True, result
    assert result["context"]["count"] == 1


def test_skill_set_aov_enabled_toggles_state():
    cmds = _arnold_cmds()
    _call_skill("add_aov", cmds=cmds, name="beauty")

    result = _call_skill("set_aov_enabled", cmds=cmds, aov="beauty", enabled=False)

    assert result["success"] is True, result
    assert result["context"]["enabled"] is False


def test_skill_set_aov_enabled_rejects_unknown_name():
    cmds = _arnold_cmds()
    _call_skill("add_aov", cmds=cmds, name="beauty")

    result = _call_skill("set_aov_enabled", cmds=cmds, aov="ghost", enabled=True)

    assert result["success"] is False


def test_skill_remove_aov_reports_remaining():
    cmds = _arnold_cmds()
    _call_skill("add_aov", cmds=cmds, name="beauty")

    result = _call_skill("remove_aov", cmds=cmds, aov="beauty")

    assert result["success"] is True, result
    assert result["context"]["remaining"] == 0


def test_skill_remove_aov_rejects_unknown_name():
    cmds = _arnold_cmds()

    result = _call_skill("remove_aov", cmds=cmds, aov="ghost")

    assert result["success"] is False


def test_load_render_setup_reports_a_useful_error_when_unavailable():
    """Fail closed with an actionable hint instead of a bare ImportError."""
    with patch.dict(sys.modules, {RENDER_SETUP_MODULE: None}):
        with pytest.raises(RenderSetupContractError, match="Render setup is unavailable"):
            render_setup_mod.load_render_setup()
