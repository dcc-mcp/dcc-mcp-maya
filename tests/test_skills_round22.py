"""Round 22: tests for maya-render-passes, maya-light-rig, maya-proxy-mesh skills."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Dynamically load a skill script module bypassing hyphenated dir names."""
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{0}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "{0}_{1}".format(skill_dir.replace("-", "_"), script_name),
        script_path,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_maya():
    """Return a fresh mock_cmds and wire maya/maya.cmds/maya.utils into sys.modules."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.utils"] = MagicMock()
    sys.modules["maya.api"] = MagicMock()
    return mock_cmds


def _cleanup_maya():
    for mod in ("maya", "maya.cmds", "maya.utils", "maya.api"):
        sys.modules.pop(mod, None)


# ===========================================================================
# maya-render-passes / create_render_pass
# ===========================================================================


class TestCreateRenderPass:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.createNode.return_value = "beautyPass1"
        self.cmds.attributeQuery.return_value = True
        self.cmds.objExists.return_value = True
        self.mod = _load_script("maya-render-passes", "create_render_pass")

    def teardown_method(self):
        _cleanup_maya()

    def test_success_basic(self):
        result = self.mod.run({"name": "beautyPass"})
        assert result.success is True
        assert "beautyPass1" in result.message

    def test_pass_type_stored(self):
        result = self.mod.run({"name": "diffPass", "pass_type": "diffuse"})
        assert result.success is True
        assert result.context["pass_type"] == "diffuse"

    def test_renderer_stored(self):
        result = self.mod.run({"name": "arnPass", "renderer": "arnold"})
        assert result.success is True
        assert result.context["renderer"] == "arnold"

    def test_cameras_associated(self):
        self.cmds.objExists.return_value = True
        result = self.mod.run({"name": "camPass", "cameras": ["camera1", "camera2"]})
        assert result.success is True
        assert len(result.context["associated_cameras"]) == 2

    def test_missing_name_returns_error(self):
        result = self.mod.run({})
        assert result.success is False
        assert "name" in result.message.lower() or "name" in result.error.lower()

    def test_empty_name_returns_error(self):
        result = self.mod.run({"name": "   "})
        assert result.success is False

    def test_exception_returns_error(self):
        self.cmds.createNode.side_effect = RuntimeError("node creation failed")
        result = self.mod.run({"name": "badPass"})
        assert result.success is False
        assert "node creation failed" in result.error


# ===========================================================================
# maya-render-passes / list_render_passes
# ===========================================================================


class TestListRenderPasses:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.ls.return_value = ["beautyPass1", "shadowPass1"]
        self.cmds.attributeQuery.return_value = True
        self.cmds.getAttr.side_effect = lambda attr, **kw: {
            "beautyPass1.passType": "beauty",
            "beautyPass1.renderer": "arnold",
            "beautyPass1.renderable": True,
            "shadowPass1.passType": "shadow",
            "shadowPass1.renderer": "maya",
            "shadowPass1.renderable": False,
        }.get(attr, "")
        self.mod = _load_script("maya-render-passes", "list_render_passes")

    def teardown_method(self):
        _cleanup_maya()

    def test_lists_all_passes(self):
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_renderer_filter(self):
        result = self.mod.run({"renderer": "arnold"})
        assert result.success is True
        assert result.context["count"] == 1
        assert result.context["passes"][0]["name"] == "beautyPass1"

    def test_enabled_only_filter(self):
        result = self.mod.run({"enabled_only": True})
        assert result.success is True
        assert result.context["count"] == 1

    def test_empty_scene(self):
        self.cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_exception_returns_error(self):
        self.cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


# ===========================================================================
# maya-render-passes / delete_render_pass
# ===========================================================================


class TestDeleteRenderPass:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.nodeType.return_value = "renderPass"
        self.mod = _load_script("maya-render-passes", "delete_render_pass")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        result = self.mod.run({"name": "beautyPass1"})
        assert result.success is True
        self.cmds.delete.assert_called_once_with("beautyPass1")

    def test_missing_name(self):
        result = self.mod.run({})
        assert result.success is False

    def test_node_not_found(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"name": "ghost"})
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_wrong_node_type(self):
        self.cmds.nodeType.return_value = "transform"
        result = self.mod.run({"name": "myTransform"})
        assert result.success is False
        assert "renderPass" in result.error

    def test_exception_returns_error(self):
        self.cmds.delete.side_effect = RuntimeError("delete failed")
        result = self.mod.run({"name": "beautyPass1"})
        assert result.success is False


# ===========================================================================
# maya-render-passes / set_render_pass_attribute
# ===========================================================================


class TestSetRenderPassAttribute:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.mod = _load_script("maya-render-passes", "set_render_pass_attribute")

    def teardown_method(self):
        _cleanup_maya()

    def test_string_attribute(self):
        result = self.mod.run({"name": "pass1", "attribute": "passType", "value": "diffuse"})
        assert result.success is True
        self.cmds.setAttr.assert_called_once_with("pass1.passType", "diffuse", type="string")

    def test_numeric_attribute(self):
        result = self.mod.run({"name": "pass1", "attribute": "renderable", "value": 1})
        assert result.success is True
        self.cmds.setAttr.assert_called_once_with("pass1.renderable", 1)

    def test_list_attribute(self):
        result = self.mod.run({"name": "pass1", "attribute": "color", "value": [1.0, 0.0, 0.0]})
        assert result.success is True
        self.cmds.setAttr.assert_called_once_with("pass1.color", 1.0, 0.0, 0.0)

    def test_missing_name(self):
        result = self.mod.run({"attribute": "x", "value": 1})
        assert result.success is False

    def test_missing_attribute(self):
        result = self.mod.run({"name": "pass1", "value": 1})
        assert result.success is False

    def test_missing_value(self):
        result = self.mod.run({"name": "pass1", "attribute": "x"})
        assert result.success is False

    def test_node_not_found(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"name": "ghost", "attribute": "x", "value": 1})
        assert result.success is False

    def test_exception_returns_error(self):
        self.cmds.setAttr.side_effect = RuntimeError("setAttr failed")
        result = self.mod.run({"name": "pass1", "attribute": "x", "value": 1})
        assert result.success is False


# ===========================================================================
# maya-render-passes / assign_pass_to_layer
# ===========================================================================


class TestAssignPassToLayer:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.nodeType.side_effect = lambda n: (
            "renderPass" if "pass" in n.lower() else "renderLayer"
        )
        self.cmds.listConnections.return_value = []
        self.cmds.getAttr.return_value = None  # no existing indices
        self.mod = _load_script("maya-render-passes", "assign_pass_to_layer")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        result = self.mod.run({"pass_name": "beautyPass1", "layer_name": "renderLayer1"})
        assert result.success is True
        self.cmds.connectAttr.assert_called_once()

    def test_missing_pass_name(self):
        result = self.mod.run({"layer_name": "layer1"})
        assert result.success is False

    def test_missing_layer_name(self):
        result = self.mod.run({"pass_name": "pass1"})
        assert result.success is False

    def test_pass_not_found(self):
        self.cmds.objExists.side_effect = lambda n: n != "beautyPass1"
        result = self.mod.run({"pass_name": "beautyPass1", "layer_name": "layer1"})
        assert result.success is False

    def test_already_connected(self):
        self.cmds.listConnections.return_value = ["renderLayer1"]
        result = self.mod.run({"pass_name": "beautyPass1", "layer_name": "renderLayer1"})
        assert result.success is True
        assert result.context["already_connected"] is True

    def test_exception_returns_error(self):
        self.cmds.connectAttr.side_effect = RuntimeError("connect failed")
        result = self.mod.run({"pass_name": "beautyPass1", "layer_name": "renderLayer1"})
        assert result.success is False


# ===========================================================================
# maya-light-rig / create_three_point_rig
# ===========================================================================


class TestCreateThreePointRig:
    def setup_method(self):
        self.cmds = _mock_maya()
        # createNode returns different names each call
        _call_count = [0]

        def _create_node(node_type, **kwargs):
            _call_count[0] += 1
            return "{}_{}".format(node_type, _call_count[0])

        self.cmds.createNode.side_effect = _create_node
        self.cmds.aimConstraint.return_value = ["aimCon1"]
        self.cmds.pointConstraint.return_value = ["ptCon1"]
        self.cmds.listRelatives.return_value = []
        self.cmds.attributeQuery.return_value = True
        self.cmds.group.return_value = "threePoint_rig_grp"
        self.mod = _load_script("maya-light-rig", "create_three_point_rig")

    def teardown_method(self):
        _cleanup_maya()

    def test_success_default(self):
        result = self.mod.run({})
        assert result.success is True
        assert "threePoint" in result.message

    def test_group_created(self):
        result = self.mod.run({"group": True})
        assert result.success is True
        assert result.context["group"] is not None

    def test_no_group(self):
        result = self.mod.run({"group": False})
        assert result.success is True
        assert result.context["group"] is None

    def test_three_lights_created(self):
        result = self.mod.run({})
        assert result.success is True
        assert len(result.context["lights"]) == 3

    def test_invalid_light_type(self):
        result = self.mod.run({"light_type": "laserBeam"})
        assert result.success is False
        assert "light_type" in result.error or "light_type" in result.message

    def test_custom_intensities(self):
        result = self.mod.run({"key_intensity": 2.0, "fill_intensity": 0.5, "back_intensity": 1.0})
        assert result.success is True

    def test_exception_returns_error(self):
        self.cmds.createNode.side_effect = RuntimeError("node failed")
        result = self.mod.run({})
        assert result.success is False


# ===========================================================================
# maya-light-rig / list_light_rigs
# ===========================================================================


class TestListLightRigs:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.ls.return_value = ["key_light_shape"]
        self.cmds.listRelatives.side_effect = lambda node, **kw: {
            "key_light_shape": ["key_light"],
            "key_light": ["|threePoint_rig_grp"],
        }.get(node, [])
        self.mod = _load_script("maya-light-rig", "list_light_rigs")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        result = self.mod.run({})
        assert result.success is True

    def test_pattern_filter(self):
        result = self.mod.run({"pattern": "threePoint"})
        assert result.success is True

    def test_no_lights_returns_empty(self):
        self.cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_exception_returns_error(self):
        self.cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


# ===========================================================================
# maya-light-rig / set_rig_intensity
# ===========================================================================


class TestSetRigIntensity:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.nodeType.return_value = "transform"
        self.cmds.listRelatives.return_value = ["|threePoint_rig_grp|key_light_shape"]
        # Make nodeType return spotLight for shapes
        self.cmds.nodeType.side_effect = lambda n: (
            "spotLight" if "shape" in n else "transform"
        )
        self.cmds.attributeQuery.return_value = True
        self.cmds.getAttr.return_value = 1.0
        self.mod = _load_script("maya-light-rig", "set_rig_intensity")

    def teardown_method(self):
        _cleanup_maya()

    def test_multiplier(self):
        result = self.mod.run({"group": "threePoint_rig_grp", "multiplier": 2.0})
        assert result.success is True

    def test_absolute(self):
        result = self.mod.run({"group": "threePoint_rig_grp", "absolute": 0.5})
        assert result.success is True

    def test_missing_group(self):
        result = self.mod.run({})
        assert result.success is False

    def test_group_not_found(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"group": "ghost_grp"})
        assert result.success is False

    def test_no_lights_in_group(self):
        self.cmds.listRelatives.return_value = []
        result = self.mod.run({"group": "empty_grp"})
        assert result.success is False
        assert "no lights" in result.message.lower()

    def test_exception_returns_error(self):
        self.cmds.listRelatives.side_effect = RuntimeError("listRel failed")
        result = self.mod.run({"group": "threePoint_rig_grp"})
        assert result.success is False


# ===========================================================================
# maya-light-rig / delete_light_rig
# ===========================================================================


class TestDeleteLightRig:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.nodeType.return_value = "transform"
        self.mod = _load_script("maya-light-rig", "delete_light_rig")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        result = self.mod.run({"group": "threePoint_rig_grp"})
        assert result.success is True
        self.cmds.delete.assert_called_once_with("threePoint_rig_grp")

    def test_missing_group(self):
        result = self.mod.run({})
        assert result.success is False

    def test_group_not_found(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"group": "ghost"})
        assert result.success is False

    def test_wrong_node_type(self):
        self.cmds.nodeType.return_value = "spotLight"
        result = self.mod.run({"group": "lightShape1"})
        assert result.success is False

    def test_exception_returns_error(self):
        self.cmds.delete.side_effect = RuntimeError("delete failed")
        result = self.mod.run({"group": "rig_grp"})
        assert result.success is False


# ===========================================================================
# maya-light-rig / add_rim_light
# ===========================================================================


class TestAddRimLight:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        _n = [0]

        def _cn(node_type, **kwargs):
            _n[0] += 1
            return "{}_{}".format(node_type, _n[0])

        self.cmds.createNode.side_effect = _cn
        self.cmds.attributeQuery.return_value = True
        self.mod = _load_script("maya-light-rig", "add_rim_light")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        result = self.mod.run({"group": "myRig_grp"})
        assert result.success is True
        assert result.context["group"] == "myRig_grp"

    def test_custom_light_type(self):
        result = self.mod.run({"group": "myRig_grp", "light_type": "areaLight"})
        assert result.success is True

    def test_custom_position(self):
        result = self.mod.run({"group": "myRig_grp", "position": [1.0, 5.0, -12.0]})
        assert result.success is True
        assert result.context["position"] == [1.0, 5.0, -12.0]

    def test_missing_group(self):
        result = self.mod.run({})
        assert result.success is False

    def test_group_not_found(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"group": "ghost"})
        assert result.success is False

    def test_invalid_light_type(self):
        result = self.mod.run({"group": "myRig_grp", "light_type": "laserBeam"})
        assert result.success is False

    def test_exception_returns_error(self):
        self.cmds.createNode.side_effect = RuntimeError("node failed")
        result = self.mod.run({"group": "myRig_grp"})
        assert result.success is False


# ===========================================================================
# maya-proxy-mesh / create_proxy
# ===========================================================================


class TestCreateProxy:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        self.cmds.polyCube.return_value = ["pSphere1_proxy", "polyCube1"]
        self.cmds.attributeQuery.return_value = False
        self.mod = _load_script("maya-proxy-mesh", "create_proxy")

    def teardown_method(self):
        _cleanup_maya()

    def test_bbox_success(self):
        result = self.mod.run({"source": "pSphere1"})
        assert result.success is True
        assert result.context["method"] == "bbox"

    def test_custom_proxy_name(self):
        result = self.mod.run({"source": "pSphere1", "proxy_name": "myProxy"})
        assert result.success is True

    def test_reduce_method(self):
        self.cmds.duplicate.return_value = ["pSphere1_proxy"]
        self.cmds.listRelatives.return_value = ["pSphere1_proxyShape"]
        self.cmds.polyEvaluate.return_value = 50
        result = self.mod.run({"source": "pSphere1", "method": "reduce", "reduce_percent": 10.0})
        assert result.success is True
        assert result.context["method"] == "reduce"

    def test_missing_source(self):
        result = self.mod.run({})
        assert result.success is False

    def test_source_not_found(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"source": "ghost"})
        assert result.success is False

    def test_invalid_method(self):
        result = self.mod.run({"source": "pSphere1", "method": "dissolve"})
        assert result.success is False
        assert "method" in result.error or "method" in result.message

    def test_hide_source(self):
        result = self.mod.run({"source": "pSphere1", "hide_source": True})
        assert result.success is True
        self.cmds.hide.assert_called_once_with("pSphere1")

    def test_exception_returns_error(self):
        self.cmds.exactWorldBoundingBox.side_effect = RuntimeError("bb failed")
        result = self.mod.run({"source": "pSphere1"})
        assert result.success is False


# ===========================================================================
# maya-proxy-mesh / swap_proxy
# ===========================================================================


class TestSwapProxy:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.mod = _load_script("maya-proxy-mesh", "swap_proxy")

    def teardown_method(self):
        _cleanup_maya()

    def test_show_proxy(self):
        result = self.mod.run({"proxy": "sphere_proxy", "source": "pSphere1", "show_proxy": True})
        assert result.success is True
        assert result.context["show_proxy"] is True
        self.cmds.showHidden.assert_called_once_with("sphere_proxy")
        self.cmds.hide.assert_called_once_with("pSphere1")

    def test_show_source(self):
        result = self.mod.run({"proxy": "sphere_proxy", "source": "pSphere1", "show_proxy": False})
        assert result.success is True
        self.cmds.showHidden.assert_called_once_with("pSphere1")
        self.cmds.hide.assert_called_once_with("sphere_proxy")

    def test_missing_proxy(self):
        result = self.mod.run({"source": "pSphere1"})
        assert result.success is False

    def test_missing_source(self):
        result = self.mod.run({"proxy": "sphere_proxy"})
        assert result.success is False

    def test_proxy_not_found(self):
        self.cmds.objExists.side_effect = lambda n: n != "sphere_proxy"
        result = self.mod.run({"proxy": "sphere_proxy", "source": "pSphere1"})
        assert result.success is False

    def test_exception_returns_error(self):
        self.cmds.showHidden.side_effect = RuntimeError("showHidden failed")
        result = self.mod.run({"proxy": "sphere_proxy", "source": "pSphere1"})
        assert result.success is False


# ===========================================================================
# maya-proxy-mesh / list_proxies
# ===========================================================================


class TestListProxies:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.ls.return_value = ["pSphere1_proxy", "pCube1_proxy", "pCube1"]
        self.cmds.attributeQuery.side_effect = lambda attr, node, exists: (
            True if node in ("pSphere1_proxy", "pCube1_proxy") else False
        )
        self.cmds.getAttr.side_effect = lambda attr, **kw: {
            "pSphere1_proxy.lod_level": 0,
            "pSphere1_proxy.visibility": True,
            "pCube1_proxy.lod_level": 0,
            "pCube1_proxy.visibility": False,
        }.get(attr, 0)
        self.cmds.listRelatives.return_value = ["proxyShape"]
        self.cmds.polyEvaluate.return_value = 6
        self.mod = _load_script("maya-proxy-mesh", "list_proxies")

    def teardown_method(self):
        _cleanup_maya()

    def test_lists_tagged_meshes(self):
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_visibility_captured(self):
        result = self.mod.run({})
        assert result.success is True
        names = [p["name"] for p in result.context["proxies"]]
        assert "pSphere1_proxy" in names

    def test_empty_scene(self):
        self.cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_exception_returns_error(self):
        self.cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


# ===========================================================================
# maya-proxy-mesh / delete_proxy
# ===========================================================================


class TestDeleteProxy:
    def setup_method(self):
        self.cmds = _mock_maya()
        self.cmds.objExists.return_value = True
        self.cmds.nodeType.return_value = "transform"
        self.mod = _load_script("maya-proxy-mesh", "delete_proxy")

    def teardown_method(self):
        _cleanup_maya()

    def test_success(self):
        result = self.mod.run({"proxy": "sphere_proxy"})
        assert result.success is True
        self.cmds.delete.assert_called_once_with("sphere_proxy")

    def test_reveal_source(self):
        result = self.mod.run({"proxy": "sphere_proxy", "reveal_source": "pSphere1"})
        assert result.success is True
        self.cmds.showHidden.assert_called_once_with("pSphere1")
        assert result.context["revealed"] == "pSphere1"

    def test_reveal_source_not_found_no_crash(self):
        self.cmds.objExists.side_effect = lambda n: n != "pSphere1"
        result = self.mod.run({"proxy": "sphere_proxy", "reveal_source": "pSphere1"})
        assert result.success is True
        assert result.context["revealed"] is None

    def test_missing_proxy(self):
        result = self.mod.run({})
        assert result.success is False

    def test_proxy_not_found(self):
        self.cmds.objExists.return_value = False
        result = self.mod.run({"proxy": "ghost"})
        assert result.success is False

    def test_wrong_node_type(self):
        self.cmds.nodeType.return_value = "mesh"
        result = self.mod.run({"proxy": "proxyShape"})
        assert result.success is False

    def test_exception_returns_error(self):
        self.cmds.delete.side_effect = RuntimeError("delete failed")
        result = self.mod.run({"proxy": "sphere_proxy"})
        assert result.success is False
