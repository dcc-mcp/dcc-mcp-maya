"""Round 5 skill tests: references / render-layers / scene-utils / uv-ops /
rigging (remaining) / mesh-ops (remaining) / node-graph (remaining).

All Maya API calls are mocked so no real Maya installation is needed.
Scripts are loaded via importlib to handle hyphenated skill directory names.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def _load_script(skill_dir, script_name):
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r5_{}_{}_{}".format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    cmds_mock.objectType.return_value = "transform"
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }
    return maya_mock, cmds_mock, modules


def _run_func(skill_dir, func_name, cmds_overrides=None, **kwargs):
    """Load a skill script, inject Maya mocks, and call its main function."""
    cmds_overrides = cmds_overrides or {}
    _, cmds_mock, modules = _make_maya_env(**cmds_overrides)
    with patch.dict(sys.modules, modules):
        mod = _load_script(skill_dir, func_name)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


# ===========================================================================
# maya-references
# ===========================================================================


class TestCreateReference:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-references", "create_reference", cmds_overrides, **kwargs)

    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.file.return_value = "charRN"
        cmds.referenceQuery.return_value = "char"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "create_reference")
            result = mod.create_reference(file_path="/scenes/char.mb")
        assert result["success"] is True
        assert result["context"]["reference_node"] == "charRN"

    def test_empty_path_returns_error(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "create_reference")
            result = mod.create_reference(file_path="")
        assert result["success"] is False

    def test_with_namespace(self):
        _, cmds, modules = _make_maya_env()
        cmds.file.return_value = "nsRN"
        cmds.referenceQuery.return_value = "myNs"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "create_reference")
            result = mod.create_reference(file_path="/scenes/x.mb", namespace="myNs")
        assert result["success"] is True

    def test_group_reference(self):
        _, cmds, modules = _make_maya_env()
        cmds.file.return_value = "grpRN"
        cmds.referenceQuery.return_value = "grp"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "create_reference")
            result = mod.create_reference(file_path="/scenes/y.mb", group_reference=True)
        assert result["success"] is True

    def test_referencequery_exception_fallback(self):
        _, cmds, modules = _make_maya_env()
        cmds.file.return_value = "someRN"
        cmds.referenceQuery.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "create_reference")
            result = mod.create_reference(file_path="/scenes/z.mb")
        assert result["success"] is True

    def test_cmds_exception_returns_error(self):
        _, cmds, modules = _make_maya_env()
        cmds.file.side_effect = RuntimeError("cmds error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "create_reference")
            result = mod.create_reference(file_path="/scenes/a.mb")
        assert result["success"] is False


class TestListReferences:
    def _load(self, cmds_overrides=None):
        _, cmds, modules = _make_maya_env(**(cmds_overrides or {}))
        return cmds, modules

    def test_no_references(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "list_references")
            result = mod.list_references()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_references(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = ["charRN", "propRN"]
        cmds.referenceQuery.side_effect = ["/char.mb", "char", True, "/prop.mb", "prop", False]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "list_references")
            result = mod.list_references()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_skips_shared_reference_node(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = ["sharedReferenceNode", "realRN"]
        cmds.referenceQuery.side_effect = ["/real.mb", "real", True]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "list_references")
            result = mod.list_references()
        assert result["context"]["count"] == 1

    def test_referencequery_exception_skips_node(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = ["brokenRN"]
        cmds.referenceQuery.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "list_references")
            result = mod.list_references()
        assert result["success"] is True
        assert result["context"]["count"] == 0


class TestRemoveReference:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "reference"
        cmds.referenceQuery.return_value = "char"
        cmds.namespace.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "remove_reference")
            result = mod.remove_reference(reference_node="charRN")
        assert result["success"] is True

    def test_node_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "remove_reference")
            result = mod.remove_reference(reference_node="missing")
        assert result["success"] is False

    def test_not_a_reference_node(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "mesh"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "remove_reference")
            result = mod.remove_reference(reference_node="pSphereShape1")
        assert result["success"] is False

    def test_without_namespace_removal(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "reference"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "remove_reference")
            result = mod.remove_reference(reference_node="charRN", remove_namespace=False)
        assert result["success"] is True
        assert result["context"]["namespace_removed"] == ""


class TestReloadReference:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "reference"
        cmds.referenceQuery.return_value = "/char.mb"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "reload_reference")
            result = mod.reload_reference(reference_node="charRN")
        assert result["success"] is True
        assert result["context"]["loaded"] is True

    def test_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "reload_reference")
            result = mod.reload_reference(reference_node="missing")
        assert result["success"] is False

    def test_not_reference_type(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "reload_reference")
            result = mod.reload_reference(reference_node="pCube1")
        assert result["success"] is False

    def test_referencequery_fallback(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "reference"
        cmds.referenceQuery.side_effect = RuntimeError("bad")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "reload_reference")
            result = mod.reload_reference(reference_node="charRN")
        assert result["success"] is True
        assert result["context"]["file_path"] == ""


class TestUnloadReference:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "reference"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "unload_reference")
            result = mod.unload_reference(reference_node="charRN")
        assert result["success"] is True
        assert result["context"]["loaded"] is False

    def test_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "unload_reference")
            result = mod.unload_reference(reference_node="missing")
        assert result["success"] is False


class TestListNamespacesRef:
    """list_namespaces in maya-references/scripts/."""

    def test_all_namespaces(self):
        _, cmds, modules = _make_maya_env()
        cmds.namespaceInfo.return_value = ["char", "prop", "UI", "shared"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "list_namespaces")
            result = mod.list_namespaces()
        assert result["success"] is True
        assert "char" in result["context"]["namespaces"]
        assert "UI" not in result["context"]["namespaces"]

    def test_root_only(self):
        _, cmds, modules = _make_maya_env()
        cmds.namespaceInfo.return_value = ["char"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "list_namespaces")
            result = mod.list_namespaces(root_only=True)
        assert result["success"] is True

    def test_empty_scene(self):
        _, cmds, modules = _make_maya_env()
        cmds.namespaceInfo.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-references", "list_namespaces")
            result = mod.list_namespaces()
        assert result["context"]["count"] == 0


# ===========================================================================
# maya-render-layers
# ===========================================================================


class TestCreateRenderLayer:
    def test_success_empty_layer(self):
        _, cmds, modules = _make_maya_env()
        cmds.createRenderLayer.return_value = "myLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "create_render_layer")
            result = mod.create_render_layer(name="myLayer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"

    def test_success_with_objects(self):
        _, cmds, modules = _make_maya_env()
        cmds.createRenderLayer.return_value = "layer1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "create_render_layer")
            result = mod.create_render_layer(name="layer1", objects=["pSphere1", "pCube1"])
        assert result["success"] is True
        assert len(result["context"]["objects_added"]) == 2

    def test_empty_name_returns_error(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "create_render_layer")
            result = mod.create_render_layer(name="")
        assert result["success"] is False

    def test_missing_object_returns_error(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.side_effect = lambda n: n != "missing"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "create_render_layer")
            result = mod.create_render_layer(name="layer1", objects=["missing"])
        assert result["success"] is False

    def test_make_current(self):
        _, cmds, modules = _make_maya_env()
        cmds.createRenderLayer.return_value = "activeLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "create_render_layer")
            result = mod.create_render_layer(name="activeLayer", make_current=True)
        assert result["context"]["is_current"] is True


class TestListRenderLayers:
    def test_returns_layers(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = ["defaultRenderLayer", "myLayer"]
        cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        cmds.editRenderLayerMembers.return_value = []
        cmds.getAttr.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "list_render_layers")
            result = mod.list_render_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exclude_default(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = ["defaultRenderLayer", "myLayer"]
        cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        cmds.editRenderLayerMembers.return_value = []
        cmds.getAttr.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "list_render_layers")
            result = mod.list_render_layers(include_default=False)
        assert result["context"]["count"] == 1

    def test_exception_in_layer_query_is_handled(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = ["myLayer"]
        cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        cmds.editRenderLayerMembers.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "list_render_layers")
            result = mod.list_render_layers()
        assert result["success"] is True


class TestSetRenderLayer:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "renderLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer")
            result = mod.set_render_layer(object_name="pSphere1", layer_name="myLayer")
        assert result["success"] is True

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.side_effect = lambda n: n != "pSphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer")
            result = mod.set_render_layer(object_name="pSphere1", layer_name="myLayer")
        assert result["success"] is False

    def test_layer_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.side_effect = lambda n: n != "myLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer")
            result = mod.set_render_layer(object_name="pSphere1", layer_name="myLayer")
        assert result["success"] is False

    def test_not_a_render_layer(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer")
            result = mod.set_render_layer(object_name="pSphere1", layer_name="pCube1")
        assert result["success"] is False


class TestDeleteRenderLayer:
    def test_cannot_delete_default(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "delete_render_layer")
            result = mod.delete_render_layer(layer_name="defaultRenderLayer")
        assert result["success"] is False

    def test_layer_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "delete_render_layer")
            result = mod.delete_render_layer(layer_name="myLayer")
        assert result["success"] is False

    def test_not_render_layer_type(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "delete_render_layer")
            result = mod.delete_render_layer(layer_name="someTransform")
        assert result["success"] is False

    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "renderLayer"
        cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "delete_render_layer")
            result = mod.delete_render_layer(layer_name="myLayer")
        assert result["success"] is True

    def test_switches_current_layer_before_delete(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "renderLayer"
        cmds.editRenderLayerGlobals.return_value = "myLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "delete_render_layer")
            result = mod.delete_render_layer(layer_name="myLayer")
        assert result["success"] is True
        cmds.editRenderLayerGlobals.assert_any_call(currentRenderLayer="defaultRenderLayer")


class TestSetRenderLayerAttribute:
    def test_set_bool_attribute(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "renderLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer_attribute")
            result = mod.set_render_layer_attribute(layer_name="myLayer", attribute="renderable", value=True)
        assert result["success"] is True

    def test_set_list_attribute(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "renderLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer_attribute")
            result = mod.set_render_layer_attribute(layer_name="myLayer", attribute="color", value=[1.0, 0.0, 0.0])
        assert result["success"] is True

    def test_set_scalar_attribute(self):
        _, cmds, modules = _make_maya_env()
        cmds.objectType.return_value = "renderLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer_attribute")
            result = mod.set_render_layer_attribute(layer_name="myLayer", attribute="passes", value=2)
        assert result["success"] is True

    def test_layer_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render-layers", "set_render_layer_attribute")
            result = mod.set_render_layer_attribute(layer_name="noLayer", attribute="renderable", value=True)
        assert result["success"] is False


# ===========================================================================
# maya-scene-utils
# ===========================================================================


class TestAlignObjects:
    def test_center_align_x(self):
        _, cmds, modules = _make_maya_env()
        cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        cmds.getAttr.return_value = 0.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["objA", "objB"], axis="x", mode="center")
        assert result["success"] is True
        assert result["context"]["axis"] == "x"

    def test_min_align_y(self):
        _, cmds, modules = _make_maya_env()
        cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        cmds.getAttr.return_value = 0.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["objA", "objB"], axis="y", mode="min")
        assert result["success"] is True

    def test_max_align_z(self):
        _, cmds, modules = _make_maya_env()
        cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        cmds.getAttr.return_value = 0.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["objA", "objB"], axis="z", mode="max")
        assert result["success"] is True

    def test_needs_at_least_two_objects(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["objA"])
        assert result["success"] is False

    def test_invalid_axis(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["a", "b"], axis="w")
        assert result["success"] is False

    def test_invalid_mode(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["a", "b"], mode="diagonal")
        assert result["success"] is False

    def test_missing_object(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.side_effect = lambda n: n != "missing"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["missing", "objB"])
        assert result["success"] is False

    def test_with_reference_object(self):
        _, cmds, modules = _make_maya_env()
        cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        cmds.getAttr.return_value = 0.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["objA", "objB"], axis="x", reference="objA")
        assert result["success"] is True

    def test_reference_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        cmds.objExists.side_effect = lambda n: n != "refMissing"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "align_objects")
            result = mod.align_objects(objects=["objA", "objB"], axis="x", reference="refMissing")
        assert result["success"] is False


class TestSetObjectColor:
    def test_set_color_index(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_object_color")
            result = mod.set_object_color(object_name="pSphere1", color_index=5)
        assert result["success"] is True
        assert result["context"]["color_index"] == 5

    def test_use_default(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_object_color")
            result = mod.set_object_color(object_name="pSphere1", color_index=5, use_default=True)
        assert result["success"] is True
        assert result["context"]["color_index"] == 0

    def test_invalid_color_index(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_object_color")
            result = mod.set_object_color(object_name="pSphere1", color_index=32)
        assert result["success"] is False

    def test_negative_color_index(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_object_color")
            result = mod.set_object_color(object_name="pSphere1", color_index=-1)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_object_color")
            result = mod.set_object_color(object_name="missing", color_index=3)
        assert result["success"] is False


class TestSetPivot:
    def test_set_both_pivots(self):
        _, cmds, modules = _make_maya_env()
        cmds.xform.return_value = [0.0, 0.0, 0.0]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_pivot")
            result = mod.set_pivot(object_name="pSphere1", position=[1.0, 2.0, 3.0])
        assert result["success"] is True

    def test_set_rotate_pivot(self):
        _, cmds, modules = _make_maya_env()
        cmds.xform.return_value = [1.0, 2.0, 3.0]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_pivot")
            result = mod.set_pivot(object_name="pSphere1", position=[1.0, 2.0, 3.0], pivot_type="rotate")
        assert result["success"] is True

    def test_invalid_pivot_type(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_pivot")
            result = mod.set_pivot(object_name="pSphere1", pivot_type="diagonal")
        assert result["success"] is False

    def test_invalid_position_length(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_pivot")
            result = mod.set_pivot(object_name="pSphere1", position=[1.0, 2.0])
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_pivot")
            result = mod.set_pivot(object_name="missing")
        assert result["success"] is False


class TestSetShadingMode:
    def test_smooth_mode(self):
        _, cmds, modules = _make_maya_env()
        cmds.getPanel.return_value = ["modelPanel1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_shading_mode")
            result = mod.set_shading_mode(mode="smooth")
        assert result["success"] is True

    def test_wireframe_mode(self):
        _, cmds, modules = _make_maya_env()
        cmds.getPanel.return_value = ["modelPanel1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_shading_mode")
            result = mod.set_shading_mode(mode="wireframe")
        assert result["success"] is True

    def test_textured_mode(self):
        _, cmds, modules = _make_maya_env()
        cmds.getPanel.return_value = ["modelPanel1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_shading_mode")
            result = mod.set_shading_mode(mode="textured")
        assert result["success"] is True

    def test_invalid_mode(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_shading_mode")
            result = mod.set_shading_mode(mode="raytraced")
        assert result["success"] is False

    def test_no_panels_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.getPanel.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_shading_mode")
            result = mod.set_shading_mode(mode="smooth")
        assert result["success"] is False

    def test_specific_panel(self):
        _, cmds, modules = _make_maya_env()
        cmds.modelPanel.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_shading_mode")
            result = mod.set_shading_mode(mode="flat", panel="modelPanel2")
        assert result["success"] is True

    def test_panel_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.modelPanel.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scene-utils", "set_shading_mode")
            result = mod.set_shading_mode(mode="smooth", panel="badPanel")
        assert result["success"] is False


# ===========================================================================
# maya-uv-ops
# ===========================================================================


class TestProjectUVs:
    def test_planar_default(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "project_uvs")
            result = mod.project_uvs(object_name="pSphere1")
        assert result["success"] is True

    def test_cylindrical(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "project_uvs")
            result = mod.project_uvs(object_name="pCyl1", projection_type="cylindrical")
        assert result["success"] is True

    def test_spherical(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "project_uvs")
            result = mod.project_uvs(object_name="pSphere1", projection_type="spherical")
        assert result["success"] is True

    def test_invalid_projection_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "project_uvs")
            result = mod.project_uvs(object_name="pSphere1", projection_type="cubic")
        assert result["success"] is False

    def test_invalid_axis(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "project_uvs")
            result = mod.project_uvs(object_name="pSphere1", axis="w")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "project_uvs")
            result = mod.project_uvs(object_name="missing")
        assert result["success"] is False


class TestUnfoldUVs:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "unfold_uvs")
            result = mod.unfold_uvs(object_name="pSphere1")
        assert result["success"] is True

    def test_with_optimize(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "unfold_uvs")
            result = mod.unfold_uvs(object_name="pSphere1", iterations=3, optimize_scale=True)
        assert result["success"] is True

    def test_invalid_iterations_zero(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "unfold_uvs")
            result = mod.unfold_uvs(object_name="pSphere1", iterations=0)
        assert result["success"] is False

    def test_iterations_too_large(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "unfold_uvs")
            result = mod.unfold_uvs(object_name="pSphere1", iterations=101)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "unfold_uvs")
            result = mod.unfold_uvs(object_name="missing")
        assert result["success"] is False


class TestNormalizeUVs:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "normalize_uvs")
            result = mod.normalize_uvs(object_name="pSphere1")
        assert result["success"] is True

    def test_invalid_layout_u_zero(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "normalize_uvs")
            result = mod.normalize_uvs(object_name="pSphere1", layout_u=0.0)
        assert result["success"] is False

    def test_invalid_layout_v_too_large(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "normalize_uvs")
            result = mod.normalize_uvs(object_name="pSphere1", layout_v=1.5)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "normalize_uvs")
            result = mod.normalize_uvs(object_name="missing")
        assert result["success"] is False


class TestGetUVInfo:
    def test_all_uv_sets(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyUVSet.return_value = ["map1", "lightMap"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "get_uv_info")
            result = mod.get_uv_info(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["uv_set_count"] == 2

    def test_specific_uv_set(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyUVSet.return_value = ["map1", "lightMap"]
        cmds.polyEditUV.return_value = [0.0, 0.5, 1.0]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "get_uv_info")
            result = mod.get_uv_info(object_name="pSphere1", uv_set="map1")
        assert result["success"] is True

    def test_uv_set_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyUVSet.return_value = ["map1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "get_uv_info")
            result = mod.get_uv_info(object_name="pSphere1", uv_set="missing")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "get_uv_info")
            result = mod.get_uv_info(object_name="missing")
        assert result["success"] is False


class TestCreateUVSet:
    def test_create_new_set(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyUVSet.return_value = ["map1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "create_uv_set")
            result = mod.create_uv_set(object_name="pSphere1", uv_set_name="bakeMap")
        assert result["success"] is True

    def test_duplicate_set_returns_error(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyUVSet.return_value = ["map1", "bakeMap"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "create_uv_set")
            result = mod.create_uv_set(object_name="pSphere1", uv_set_name="bakeMap")
        assert result["success"] is False

    def test_copy_from_existing(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyUVSet.return_value = ["map1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "create_uv_set")
            result = mod.create_uv_set(object_name="pSphere1", uv_set_name="newMap", copy_from="map1")
        assert result["success"] is True

    def test_copy_from_missing_source(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyUVSet.return_value = ["map1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "create_uv_set")
            result = mod.create_uv_set(object_name="pSphere1", uv_set_name="newMap", copy_from="noSuchSet")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-uv-ops", "create_uv_set")
            result = mod.create_uv_set(object_name="missing", uv_set_name="map2")
        assert result["success"] is False


# ===========================================================================
# maya-rigging (remaining)
# ===========================================================================


class TestAssignDeformer:
    def test_cluster(self):
        _, cmds, modules = _make_maya_env()
        cmds.cluster.return_value = ["clusterDeformer1", "clusterHandle1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            result = mod.assign_deformer(object_name="pSphere1", deformer_type="cluster")
        assert result["success"] is True
        assert result["context"]["deformer_type"] == "cluster"

    def test_lattice(self):
        _, cmds, modules = _make_maya_env()
        cmds.lattice.return_value = ["ffd1Lattice"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            result = mod.assign_deformer(object_name="pSphere1", deformer_type="lattice")
        assert result["success"] is True

    def test_nonlinear_bend(self):
        _, cmds, modules = _make_maya_env()
        cmds.nonLinear.return_value = ["bend1", "bend1Handle"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            result = mod.assign_deformer(object_name="pSphere1", deformer_type="bend")
        assert result["success"] is True

    def test_generic_blendshape(self):
        _, cmds, modules = _make_maya_env()
        cmds.deformer.return_value = ["blendShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            result = mod.assign_deformer(object_name="pSphere1", deformer_type="blendShape")
        assert result["success"] is True

    def test_unsupported_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            result = mod.assign_deformer(object_name="pSphere1", deformer_type="fluids")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "assign_deformer")
            result = mod.assign_deformer(object_name="missing")
        assert result["success"] is False


class TestCreateCurve:
    def test_default_curve(self):
        _, cmds, modules = _make_maya_env()
        cmds.curve.return_value = "curve1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "create_curve")
            result = mod.create_curve()
        assert result["success"] is True
        assert result["context"]["object_name"] == "curve1"

    def test_with_custom_points(self):
        _, cmds, modules = _make_maya_env()
        cmds.curve.return_value = "curve2"
        pts = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "create_curve")
            result = mod.create_curve(points=pts, degree=3)
        assert result["success"] is True
        assert result["context"]["point_count"] == 4

    def test_too_few_points(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "create_curve")
            result = mod.create_curve(points=[[0, 0, 0]], degree=3)
        assert result["success"] is False

    def test_with_name(self):
        _, cmds, modules = _make_maya_env()
        cmds.curve.return_value = "mySpline"
        pts = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "create_curve")
            result = mod.create_curve(points=pts, name="mySpline")
        assert result["context"]["object_name"] == "mySpline"

    def test_periodic_curve(self):
        _, cmds, modules = _make_maya_env()
        cmds.curve.return_value = "periodicCurve1"
        pts = [[0, 0, 0], [1, 1, 0], [2, 0, 0], [3, -1, 0]]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "create_curve")
            result = mod.create_curve(points=pts, periodic=True)
        assert result["success"] is True


class TestSetDrivenKey:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_driven_key")
            result = mod.set_driven_key(
                driver_attr="ctrl.rotateY",
                driven_attrs=["joint1.translateX"],
                driver_values=[0.0, 90.0],
                driven_values=[[0.0], [5.0]],
            )
        assert result["success"] is True
        assert result["context"]["key_count"] == 2

    def test_empty_driver_values(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_driven_key")
            result = mod.set_driven_key(
                driver_attr="ctrl.rotateY",
                driven_attrs=["joint1.tx"],
                driver_values=[],
                driven_values=[],
            )
        assert result["success"] is False

    def test_mismatched_value_lengths(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_driven_key")
            result = mod.set_driven_key(
                driver_attr="ctrl.rotateY",
                driven_attrs=["joint1.tx"],
                driver_values=[0.0, 90.0],
                driven_values=[[0.0]],
            )
        assert result["success"] is False

    def test_invalid_tangent_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_driven_key")
            result = mod.set_driven_key(
                driver_attr="ctrl.rotateY",
                driven_attrs=["joint1.tx"],
                driver_values=[0.0],
                driven_values=[[0.0]],
                tangent_type="bezier",
            )
        assert result["success"] is False

    def test_driver_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.side_effect = lambda n: n != "ctrl"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-rigging", "set_driven_key")
            result = mod.set_driven_key(
                driver_attr="ctrl.rotateY",
                driven_attrs=["joint1.tx"],
                driver_values=[0.0],
                driven_values=[[0.0]],
            )
        assert result["success"] is False


# ===========================================================================
# maya-mesh-ops (remaining)
# ===========================================================================


class TestApplySubdivision:
    def test_preview_method(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = ["pSphereShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            result = mod.apply_subdivision(object_name="pSphere1", method="preview")
        assert result["success"] is True

    def test_subdivide_method(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = ["pSphereShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            result = mod.apply_subdivision(object_name="pSphere1", method="subdivide")
        assert result["success"] is True

    def test_invalid_method(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            result = mod.apply_subdivision(object_name="pSphere1", method="catmullclark")
        assert result["success"] is False

    def test_no_mesh_shape(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = []
        cmds.objectType.return_value = "camera"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            result = mod.apply_subdivision(object_name="myCam")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            result = mod.apply_subdivision(object_name="missing")
        assert result["success"] is False

    def test_direct_mesh_shape(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = []
        cmds.objectType.return_value = "mesh"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "apply_subdivision")
            result = mod.apply_subdivision(object_name="pSphereShape1", method="preview")
        assert result["success"] is True


class TestCleanupMesh:
    def test_success_all_options(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "cleanup_mesh")
            result = mod.cleanup_mesh(object_name="pSphere1")
        assert result["success"] is True

    def test_only_non_manifold(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "cleanup_mesh")
            result = mod.cleanup_mesh(
                object_name="pSphere1",
                non_manifold=True,
                lamina_faces=False,
                invalid_components=False,
            )
        assert result["success"] is True

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "cleanup_mesh")
            result = mod.cleanup_mesh(object_name="missing")
        assert result["success"] is False


class TestCreateProxyMesh:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = ["pSphereShape1"]
        cmds.polyEvaluate.side_effect = [100, 50]
        cmds.duplicate.return_value = ["pSphere1_proxy"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "create_proxy_mesh")
            result = mod.create_proxy_mesh(object_name="pSphere1", reduction=0.5)
        assert result["success"] is True
        assert result["context"]["proxy_mesh"] == "pSphere1_proxy"

    def test_invalid_reduction_one(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "create_proxy_mesh")
            result = mod.create_proxy_mesh(object_name="pSphere1", reduction=1.0)
        assert result["success"] is False

    def test_zero_reduction_is_valid(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = ["shape1"]
        cmds.polyEvaluate.return_value = 100
        cmds.duplicate.return_value = ["copy1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "create_proxy_mesh")
            result = mod.create_proxy_mesh(object_name="pSphere1", reduction=0.0)
        assert result["success"] is True

    def test_no_mesh_shape(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = []
        cmds.objectType.return_value = "joint"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "create_proxy_mesh")
            result = mod.create_proxy_mesh(object_name="joint1", reduction=0.5)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "create_proxy_mesh")
            result = mod.create_proxy_mesh(object_name="missing", reduction=0.5)
        assert result["success"] is False


class TestExtractFaces:
    def test_success_with_separate(self):
        _, cmds, modules = _make_maya_env()
        cmds.polySeparate.return_value = ["newMesh"]
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "extract_faces")
            result = mod.extract_faces(object_name="pSphere1", face_indices=[0, 1, 2])
        assert result["success"] is True
        assert result["context"]["face_count"] == 3

    def test_empty_object_name(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "extract_faces")
            result = mod.extract_faces(object_name="", face_indices=[0])
        assert result["success"] is False

    def test_empty_face_indices(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "extract_faces")
            result = mod.extract_faces(object_name="pSphere1", face_indices=[])
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "extract_faces")
            result = mod.extract_faces(object_name="missing", face_indices=[0, 1])
        assert result["success"] is False

    def test_no_separate(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "extract_faces")
            result = mod.extract_faces(object_name="pSphere1", face_indices=[0, 1], separate=False)
        assert result["success"] is True


class TestMergeVertices:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyEvaluate.side_effect = [100, 95]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "merge_vertices")
            result = mod.merge_vertices(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["merged_count"] == 5

    def test_custom_threshold(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyEvaluate.side_effect = [50, 48]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "merge_vertices")
            result = mod.merge_vertices(object_name="pSphere1", threshold=0.01)
        assert result["success"] is True

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "merge_vertices")
            result = mod.merge_vertices(object_name="missing")
        assert result["success"] is False


class TestSelectByMaterial:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.listConnections.return_value = ["sg1"]
        cmds.sets.return_value = ["pSphere1"]
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "select_by_material")
            result = mod.select_by_material(material_name="lambert1")
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_material_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "select_by_material")
            result = mod.select_by_material(material_name="missing")
        assert result["success"] is False

    def test_no_shading_groups(self):
        _, cmds, modules = _make_maya_env()
        cmds.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "select_by_material")
            result = mod.select_by_material(material_name="lambert1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_mesh_shape_resolved_to_transform(self):
        _, cmds, modules = _make_maya_env()
        cmds.listConnections.return_value = ["sg1"]
        cmds.sets.return_value = ["pSphereShape1"]
        cmds.objectType.return_value = "mesh"
        cmds.listRelatives.return_value = ["pSphere1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "select_by_material")
            result = mod.select_by_material(material_name="blinn1")
        assert result["success"] is True
        assert "pSphere1" in result["context"]["objects"]


class TestSeparateMesh:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.polySeparate.return_value = ["mesh1", "mesh2"]
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "separate_mesh")
            result = mod.separate_mesh(object_name="combined")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_empty_name(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "separate_mesh")
            result = mod.separate_mesh(object_name="")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "separate_mesh")
            result = mod.separate_mesh(object_name="missing")
        assert result["success"] is False

    def test_deduplication(self):
        _, cmds, modules = _make_maya_env()
        cmds.polySeparate.return_value = ["mesh1", "mesh1", "mesh2"]
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "separate_mesh")
            result = mod.separate_mesh(object_name="combined")
        assert result["context"]["count"] == 2


class TestGetMeshEdgeInfo:
    def _setup_cmds(self, modules):
        _, cmds, _ = _make_maya_env()
        cmds.polyEvaluate.return_value = 12
        cmds.polyInfo.return_value = ["EDGE 0 : 0 1"]
        cmds.pointPosition.side_effect = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
        return cmds

    def test_specific_edges(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyEvaluate.return_value = 12
        cmds.polyInfo.return_value = ["EDGE 0 : 0 1"]
        cmds.pointPosition.side_effect = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "get_mesh_edge_info")
            result = mod.get_mesh_edge_info(object_name="pSphere1", edge_indices=[0])
        assert result["success"] is True
        assert result["context"]["edge_count"] == 1

    def test_invalid_edge_index(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyEvaluate.return_value = 12
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "get_mesh_edge_info")
            result = mod.get_mesh_edge_info(object_name="pSphere1", edge_indices=[999])
        assert result["success"] is False

    def test_no_edges_returns_error(self):
        _, cmds, modules = _make_maya_env()
        cmds.polyEvaluate.return_value = 0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "get_mesh_edge_info")
            result = mod.get_mesh_edge_info(object_name="pSphere1")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-mesh-ops", "get_mesh_edge_info")
            result = mod.get_mesh_edge_info(object_name="missing")
        assert result["success"] is False


# ===========================================================================
# maya-node-graph (remaining)
# ===========================================================================


class TestApplySymmetry:
    def test_x_axis(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "apply_symmetry")
            result = mod.apply_symmetry(object_name="pSphere1", axis="x")
        assert result["success"] is True

    def test_disable_symmetry(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "apply_symmetry")
            result = mod.apply_symmetry(object_name="pSphere1", axis="none")
        assert result["success"] is True

    def test_invalid_axis(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "apply_symmetry")
            result = mod.apply_symmetry(object_name="pSphere1", axis="w")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "apply_symmetry")
            result = mod.apply_symmetry(object_name="missing")
        assert result["success"] is False


class TestDeleteHistory:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "delete_history")
            result = mod.delete_history(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "delete_history")
            result = mod.delete_history(object_name="missing")
        assert result["success"] is False


class TestGetDagPath:
    def test_success(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = ["|group1|pSphere1"]
        cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "get_dag_path")
            result = mod.get_dag_path(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["dag_path"] == "|group1|pSphere1"
        assert result["context"]["short_name"] == "pSphere1"

    def test_empty_ls_result(self):
        _, cmds, modules = _make_maya_env()
        cmds.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "get_dag_path")
            result = mod.get_dag_path(object_name="pSphere1")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "get_dag_path")
            result = mod.get_dag_path(object_name="missing")
        assert result["success"] is False


class TestListHistory:
    def test_returns_history(self):
        _, cmds, modules = _make_maya_env()
        cmds.listHistory.return_value = ["polyExtrudeFace1", "polyCylinder1"]
        cmds.objectType.side_effect = ["polyExtrudeFace", "polyCylinder"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "list_history")
            result = mod.list_history(object_name="pCylinder1")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_no_history(self):
        _, cmds, modules = _make_maya_env()
        cmds.listHistory.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "list_history")
            result = mod.list_history(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "list_history")
            result = mod.list_history(object_name="missing")
        assert result["success"] is False

    def test_future_flag(self):
        _, cmds, modules = _make_maya_env()
        cmds.listHistory.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "list_history")
            result = mod.list_history(object_name="pSphere1", future=True)
        assert result["success"] is True
        assert result["context"]["future"] is True


class TestSmoothMesh:
    def test_preview_mode(self):
        _, cmds, modules = _make_maya_env()
        cmds.listRelatives.return_value = ["|pSphere1|pSphereShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "smooth_mesh")
            result = mod.smooth_mesh(object_name="pSphere1", method="preview")
        assert result["success"] is True

    def test_subdivide_mode(self):
        _, cmds, modules = _make_maya_env()
        cmds.polySmooth.return_value = ["polySmoothFace1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "smooth_mesh")
            result = mod.smooth_mesh(object_name="pSphere1", method="subdivide", divisions=2)
        assert result["success"] is True
        assert result["context"]["method"] == "subdivide"

    def test_invalid_method(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "smooth_mesh")
            result = mod.smooth_mesh(object_name="pSphere1", method="catmull")
        assert result["success"] is False

    def test_negative_divisions(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "smooth_mesh")
            result = mod.smooth_mesh(object_name="pSphere1", divisions=-1)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "smooth_mesh")
            result = mod.smooth_mesh(object_name="missing")
        assert result["success"] is False


class TestTransferAttributes:
    def test_success_defaults(self):
        _, cmds, modules = _make_maya_env()
        cmds.transferAttributes.return_value = ["transferAttributes1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "transfer_attributes")
            result = mod.transfer_attributes(source="srcMesh", target="dstMesh")
        assert result["success"] is True
        assert result["context"]["transfer_node"] == "transferAttributes1"

    def test_source_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.side_effect = lambda n: n != "srcMesh"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "transfer_attributes")
            result = mod.transfer_attributes(source="srcMesh", target="dstMesh")
        assert result["success"] is False

    def test_target_not_found(self):
        _, cmds, modules = _make_maya_env()
        cmds.objExists.side_effect = lambda n: n != "dstMesh"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "transfer_attributes")
            result = mod.transfer_attributes(source="srcMesh", target="dstMesh")
        assert result["success"] is False

    def test_invalid_sample_space(self):
        _, cmds, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "transfer_attributes")
            result = mod.transfer_attributes(source="srcMesh", target="dstMesh", sample_space=99)
        assert result["success"] is False

    def test_all_transfer_flags(self):
        _, cmds, modules = _make_maya_env()
        cmds.transferAttributes.return_value = ["ta1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-node-graph", "transfer_attributes")
            result = mod.transfer_attributes(
                source="src",
                target="dst",
                transfer_positions=True,
                transfer_normals=True,
                transfer_uvs=True,
                transfer_colors=True,
            )
        assert result["success"] is True
