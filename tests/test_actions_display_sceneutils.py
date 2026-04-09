"""Tests for display layer actions, scene_utils actions, and transfer_attributes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Shared Maya mock fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Inject a minimal maya.cmds mock for every test in this module."""
    cmds = MagicMock()

    # Default helpers used across many tests
    cmds.objExists.return_value = True
    cmds.objectType.return_value = "transform"
    cmds.ls.return_value = []
    cmds.createDisplayLayer.return_value = "layer1"
    cmds.editDisplayLayerMembers.return_value = []
    cmds.getAttr.return_value = 1
    cmds.xform.return_value = [0.0, 0.0, 0.0]
    cmds.exactWorldBoundingBox.return_value = [-0.5, -0.5, -0.5, 0.5, 0.5, 0.5]
    cmds.annotate.return_value = "annotationShape1"
    cmds.listRelatives.return_value = ["annotation1"]
    cmds.transferAttributes.return_value = ["transferAttributes1"]

    mock_maya_mod = MagicMock()
    mock_maya_mod.cmds = cmds
    monkeypatch.setitem(sys.modules, "maya", mock_maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)

    mock_core = MagicMock()

    def _success(msg, **kwargs):
        m = MagicMock()
        m.to_dict.return_value = {"success": True, "message": msg, "context": kwargs}
        return m

    def _error(msg, detail=""):
        m = MagicMock()
        m.to_dict.return_value = {"success": False, "message": msg, "context": {"detail": detail}}
        return m

    mock_core.success_result.side_effect = _success
    mock_core.error_result.side_effect = _error
    monkeypatch.setitem(sys.modules, "dcc_mcp_core", mock_core)

    return cmds


# ===========================================================================
# TestCreateDisplayLayer
# ===========================================================================


class TestCreateDisplayLayer:
    def test_create_empty_layer(self, mock_maya):
        from dcc_mcp_maya.actions.display import create_display_layer

        result = create_display_layer(name="myLayer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "layer1"
        assert result["context"]["objects_added"] == []

    def test_create_layer_with_objects(self, mock_maya):
        from dcc_mcp_maya.actions.display import create_display_layer

        result = create_display_layer(name="myLayer", objects=["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["objects_added"] == ["pSphere1", "pCube1"]
        mock_maya.editDisplayLayerMembers.assert_called_once()

    def test_create_layer_empty_name(self, mock_maya):
        from dcc_mcp_maya.actions.display import create_display_layer

        result = create_display_layer(name="  ")
        assert result["success"] is False
        assert "name" in result["message"].lower() or "invalid" in result["message"].lower()

    def test_create_layer_invalid_display_type(self, mock_maya):
        from dcc_mcp_maya.actions.display import create_display_layer

        result = create_display_layer(name="myLayer", display_type=5)
        assert result["success"] is False
        assert "display_type" in result["message"]

    def test_create_layer_missing_objects(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "missing_obj"
        from dcc_mcp_maya.actions.display import create_display_layer

        result = create_display_layer(name="myLayer", objects=["missing_obj"])
        assert result["success"] is False
        assert "missing_obj" in result["message"]

    def test_create_layer_invisible(self, mock_maya):
        from dcc_mcp_maya.actions.display import create_display_layer

        result = create_display_layer(name="hiddenLayer", visible=False)
        assert result["success"] is True
        mock_maya.setAttr.assert_any_call("layer1.visibility", False)

    def test_create_layer_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        import importlib
        import dcc_mcp_maya.actions.display as mod
        importlib.reload(mod)
        # Re-patch after reload
        mock_core = MagicMock()

        def _error(msg, detail=""):
            m = MagicMock()
            m.to_dict.return_value = {"success": False, "message": msg}
            return m

        mock_core.error_result.side_effect = _error
        monkeypatch.setitem(sys.modules, "dcc_mcp_core", mock_core)

        with patch.dict(sys.modules, {"maya.cmds": None}):
            from dcc_mcp_maya.actions.display import create_display_layer
            result = create_display_layer(name="layer")
            assert result["success"] is False

    def test_create_layer_exception(self, mock_maya):
        mock_maya.createDisplayLayer.side_effect = RuntimeError("boom")
        from dcc_mcp_maya.actions.display import create_display_layer

        result = create_display_layer(name="myLayer")
        assert result["success"] is False
        assert "boom" in result["context"]["detail"]


# ===========================================================================
# TestSetDisplayLayer
# ===========================================================================


class TestSetDisplayLayer:
    def test_set_layer_success(self, mock_maya):
        mock_maya.objectType.return_value = "displayLayer"
        from dcc_mcp_maya.actions.display import set_display_layer

        result = set_display_layer(object_name="pSphere1", layer_name="layer1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"
        assert result["context"]["layer_name"] == "layer1"

    def test_set_layer_object_missing(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "missing"
        from dcc_mcp_maya.actions.display import set_display_layer

        result = set_display_layer(object_name="missing", layer_name="layer1")
        assert result["success"] is False

    def test_set_layer_layer_missing(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "noLayer"
        from dcc_mcp_maya.actions.display import set_display_layer

        result = set_display_layer(object_name="pSphere1", layer_name="noLayer")
        assert result["success"] is False

    def test_set_layer_wrong_type(self, mock_maya):
        mock_maya.objectType.return_value = "transform"
        from dcc_mcp_maya.actions.display import set_display_layer

        result = set_display_layer(object_name="pSphere1", layer_name="someTransform")
        assert result["success"] is False
        assert "display layer" in result["message"].lower() or "displayLayer" in result["message"]

    def test_set_layer_exception(self, mock_maya):
        mock_maya.objectType.return_value = "displayLayer"
        mock_maya.editDisplayLayerMembers.side_effect = RuntimeError("err")
        from dcc_mcp_maya.actions.display import set_display_layer

        result = set_display_layer(object_name="pSphere1", layer_name="layer1")
        assert result["success"] is False


# ===========================================================================
# TestDeleteDisplayLayer
# ===========================================================================


class TestDeleteDisplayLayer:
    def test_delete_layer_success(self, mock_maya):
        mock_maya.objectType.return_value = "displayLayer"
        mock_maya.editDisplayLayerMembers.return_value = []
        from dcc_mcp_maya.actions.display import delete_display_layer

        result = delete_display_layer(layer_name="layer1")
        assert result["success"] is True
        mock_maya.delete.assert_called_with("layer1")

    def test_delete_default_layer_blocked(self, mock_maya):
        from dcc_mcp_maya.actions.display import delete_display_layer

        result = delete_display_layer(layer_name="defaultLayer")
        assert result["success"] is False
        assert "defaultLayer" in result["message"]

    def test_delete_missing_layer(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.display import delete_display_layer

        result = delete_display_layer(layer_name="noLayer")
        assert result["success"] is False

    def test_delete_wrong_type(self, mock_maya):
        mock_maya.objectType.return_value = "transform"
        from dcc_mcp_maya.actions.display import delete_display_layer

        result = delete_display_layer(layer_name="someNode")
        assert result["success"] is False

    def test_delete_layer_with_objects(self, mock_maya):
        mock_maya.objectType.return_value = "displayLayer"
        mock_maya.editDisplayLayerMembers.return_value = ["pSphere1", "pCube1"]
        from dcc_mcp_maya.actions.display import delete_display_layer

        result = delete_display_layer(layer_name="layer1", remove_objects=True)
        assert result["success"] is True
        assert result["context"]["objects_deleted"] == ["pSphere1", "pCube1"]

    def test_delete_layer_exception(self, mock_maya):
        mock_maya.objectType.return_value = "displayLayer"
        mock_maya.delete.side_effect = RuntimeError("boom")
        from dcc_mcp_maya.actions.display import delete_display_layer

        result = delete_display_layer(layer_name="layer1")
        assert result["success"] is False


# ===========================================================================
# TestListDisplayLayers
# ===========================================================================


class TestListDisplayLayers:
    def test_list_layers_empty(self, mock_maya):
        mock_maya.ls.return_value = []
        from dcc_mcp_maya.actions.display import list_display_layers

        result = list_display_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_layers_with_results(self, mock_maya):
        mock_maya.ls.return_value = ["defaultLayer", "layer1"]
        mock_maya.editDisplayLayerMembers.return_value = ["pSphere1"]
        mock_maya.getAttr.return_value = 1
        from dcc_mcp_maya.actions.display import list_display_layers

        result = list_display_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_list_layers_exception(self, mock_maya):
        mock_maya.ls.side_effect = RuntimeError("err")
        from dcc_mcp_maya.actions.display import list_display_layers

        result = list_display_layers()
        assert result["success"] is False


# ===========================================================================
# TestSetPivot
# ===========================================================================


class TestSetPivot:
    def test_set_pivot_both(self, mock_maya):
        mock_maya.xform.return_value = [0.0, 1.0, 0.0]
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="pSphere1", position=[0, 1, 0])
        assert result["success"] is True
        assert result["context"]["pivot_type"] == "both"

    def test_set_pivot_rotate_only(self, mock_maya):
        mock_maya.xform.return_value = [0.0, 0.0, 0.0]
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="pSphere1", position=[1, 0, 0], pivot_type="rotate")
        assert result["success"] is True
        assert result["context"]["pivot_type"] == "rotate"

    def test_set_pivot_scale_only(self, mock_maya):
        mock_maya.xform.return_value = [0.0, 0.0, 0.0]
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="pSphere1", position=[0, 0, 2], pivot_type="scale")
        assert result["success"] is True

    def test_set_pivot_invalid_pivot_type(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="pSphere1", position=[0, 0, 0], pivot_type="wrong")
        assert result["success"] is False
        assert "pivot_type" in result["message"]

    def test_set_pivot_invalid_position_length(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="pSphere1", position=[1, 2])
        assert result["success"] is False
        assert "position" in result["message"]

    def test_set_pivot_object_missing(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="missing")
        assert result["success"] is False

    def test_set_pivot_no_position_query_only(self, mock_maya):
        mock_maya.xform.return_value = [0.0, 0.0, 0.0]
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="pSphere1")
        assert result["success"] is True

    def test_set_pivot_exception(self, mock_maya):
        mock_maya.xform.side_effect = RuntimeError("bad")
        from dcc_mcp_maya.actions.scene_utils import set_pivot

        result = set_pivot(object_name="pSphere1", position=[0, 0, 0])
        assert result["success"] is False


# ===========================================================================
# TestAlignObjects
# ===========================================================================


class TestAlignObjects:
    def _bb(self, center_x=0.0, center_y=0.0, center_z=0.0):
        """Return a bounding box [xmin, ymin, zmin, xmax, ymax, zmax]."""
        return [center_x - 0.5, center_y - 0.5, center_z - 0.5,
                center_x + 0.5, center_y + 0.5, center_z + 0.5]

    def test_align_center_x(self, mock_maya):
        mock_maya.exactWorldBoundingBox.side_effect = [
            self._bb(0.0), self._bb(5.0),  # combined query
            self._bb(0.0), self._bb(5.0),  # per-object
        ]
        mock_maya.getAttr.return_value = 0.0
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["pSphere1", "pCube1"], axis="x", mode="center")
        assert result["success"] is True
        assert result["context"]["axis"] == "x"
        assert result["context"]["mode"] == "center"

    def test_align_min_y(self, mock_maya):
        mock_maya.exactWorldBoundingBox.side_effect = [
            self._bb(0, 0, 0), self._bb(0, 3, 0),
            self._bb(0, 0, 0), self._bb(0, 3, 0),
        ]
        mock_maya.getAttr.return_value = 0.0
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["a", "b"], axis="y", mode="min")
        assert result["success"] is True

    def test_align_max_z(self, mock_maya):
        mock_maya.exactWorldBoundingBox.side_effect = [
            self._bb(0, 0, 0), self._bb(0, 0, 4),
            self._bb(0, 0, 0), self._bb(0, 0, 4),
        ]
        mock_maya.getAttr.return_value = 0.0
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["a", "b"], axis="z", mode="max")
        assert result["success"] is True

    def test_align_with_reference(self, mock_maya):
        mock_maya.exactWorldBoundingBox.side_effect = [
            self._bb(10.0),  # reference bb
            self._bb(0.0), self._bb(5.0),  # per-object
        ]
        mock_maya.getAttr.return_value = 0.0
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["a", "b"], axis="x", mode="center", reference="refObj")
        assert result["success"] is True
        assert result["context"]["target_value"] == pytest.approx(10.0)

    def test_align_too_few_objects(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["only_one"])
        assert result["success"] is False
        assert "insufficient" in result["message"].lower() or "2" in result["message"] or "least" in result["message"]

    def test_align_invalid_axis(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["a", "b"], axis="w")
        assert result["success"] is False
        assert "axis" in result["message"]

    def test_align_invalid_mode(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["a", "b"], mode="middle")
        assert result["success"] is False
        assert "mode" in result["message"]

    def test_align_missing_objects(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "missing"
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["missing", "pSphere1"])
        assert result["success"] is False

    def test_align_missing_reference(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "noRef"
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["a", "b"], reference="noRef")
        assert result["success"] is False

    def test_align_exception(self, mock_maya):
        mock_maya.exactWorldBoundingBox.side_effect = RuntimeError("bb error")
        from dcc_mcp_maya.actions.scene_utils import align_objects

        result = align_objects(objects=["a", "b"])
        assert result["success"] is False


# ===========================================================================
# TestCreateAnnotation
# ===========================================================================


class TestCreateAnnotation:
    def test_create_annotation_default_position(self, mock_maya):
        mock_maya.xform.return_value = [0.0, 0.0, 0.0]
        from dcc_mcp_maya.actions.scene_utils import create_annotation

        result = create_annotation(object_name="pSphere1", text="Hello!")
        assert result["success"] is True
        assert result["context"]["text"] == "Hello!"
        assert result["context"]["annotation_transform"] == "annotation1"

    def test_create_annotation_custom_position(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import create_annotation

        result = create_annotation(object_name="pSphere1", text="Note", position=[1, 2, 3])
        assert result["success"] is True
        assert result["context"]["position"] == [1.0, 2.0, 3.0]

    def test_create_annotation_missing_object(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene_utils import create_annotation

        result = create_annotation(object_name="missing", text="test")
        assert result["success"] is False

    def test_create_annotation_empty_text(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import create_annotation

        result = create_annotation(object_name="pSphere1", text="")
        assert result["success"] is False
        assert "text" in result["message"].lower() or "empty" in result["message"].lower()

    def test_create_annotation_invalid_position(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import create_annotation

        result = create_annotation(object_name="pSphere1", text="x", position=[1, 2])
        assert result["success"] is False
        assert "position" in result["message"]

    def test_create_annotation_no_parent(self, mock_maya):
        """When listRelatives returns None, annotation_transform falls back to shape name."""
        mock_maya.xform.return_value = [0.0, 0.0, 0.0]
        mock_maya.listRelatives.return_value = None
        from dcc_mcp_maya.actions.scene_utils import create_annotation

        result = create_annotation(object_name="pSphere1", text="test")
        assert result["success"] is True
        # Falls back to the shape node name
        assert result["context"]["annotation_transform"] == "annotationShape1"

    def test_create_annotation_exception(self, mock_maya):
        mock_maya.xform.side_effect = RuntimeError("xform fail")
        from dcc_mcp_maya.actions.scene_utils import create_annotation

        result = create_annotation(object_name="pSphere1", text="test")
        assert result["success"] is False


# ===========================================================================
# TestTransferAttributes
# ===========================================================================


class TestTransferAttributes:
    def test_transfer_defaults(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(source="mesh1", target="mesh2")
        assert result["success"] is True
        assert result["context"]["source"] == "mesh1"
        assert result["context"]["target"] == "mesh2"
        assert result["context"]["transfer_node"] == "transferAttributes1"

    def test_transfer_source_missing(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "mesh1"
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(source="mesh1", target="mesh2")
        assert result["success"] is False
        assert "mesh1" in result["message"]

    def test_transfer_target_missing(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "mesh2"
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(source="mesh1", target="mesh2")
        assert result["success"] is False
        assert "mesh2" in result["message"]

    def test_transfer_invalid_sample_space(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(source="mesh1", target="mesh2", sample_space=99)
        assert result["success"] is False
        assert "sample_space" in result["message"]

    def test_transfer_positions(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(source="mesh1", target="mesh2", transfer_positions=True)
        assert result["success"] is True
        assert result["context"]["transfer_positions"] is True

    def test_transfer_colors(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(
            source="mesh1", target="mesh2", transfer_colors=True, transfer_uvs=False
        )
        assert result["success"] is True
        assert result["context"]["transfer_colors"] is True

    def test_transfer_no_result_node(self, mock_maya):
        mock_maya.transferAttributes.return_value = []
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(source="mesh1", target="mesh2")
        assert result["success"] is True
        assert result["context"]["transfer_node"] == "transferAttributes1"

    def test_transfer_exception(self, mock_maya):
        mock_maya.transferAttributes.side_effect = RuntimeError("xfer fail")
        from dcc_mcp_maya.actions.node_graph import transfer_attributes

        result = transfer_attributes(source="mesh1", target="mesh2")
        assert result["success"] is False
        assert "xfer fail" in result["context"]["detail"]


# ===========================================================================
# TestRegisterAllRound8
# ===========================================================================


class TestRegisterAllRound8:
    def test_all_new_actions_in_all(self):
        from dcc_mcp_maya.actions import __all__

        new_actions = [
            "create_display_layer",
            "set_display_layer",
            "delete_display_layer",
            "list_display_layers",
            "set_pivot",
            "align_objects",
            "create_annotation",
            "transfer_attributes",
        ]
        for action in new_actions:
            assert action in __all__, "{} not found in __all__".format(action)

    def test_register_all_count(self):
        from dcc_mcp_maya.actions import register_all

        registry = MagicMock()
        registered = []
        registry.register.side_effect = lambda name, **kw: registered.append(name)
        register_all(registry)
        assert len(registered) >= 79, "Expected at least 79 registered actions, got {}".format(
            len(registered)
        )
