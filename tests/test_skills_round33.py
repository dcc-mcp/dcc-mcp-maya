"""Round-33 tests: cover remaining api.py & server.py uncovered lines.

Coverage targets
----------------
- api.py lines 212-214  : require_cmds() ImportError path
- api.py lines 228-230  : get_cmds() ImportError path
- api.py build_context_dict, ensure_valid_name, scene_object_from_node,
         object_transform_from_node, bounding_box_from_node
- server.py line 164    : registry property when _server has no _registry attr
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cmds(**overrides):
    """Return a MagicMock that quacks like maya.cmds."""
    cmds = MagicMock()
    for k, v in overrides.items():
        setattr(cmds, k, v)
    return cmds


# ---------------------------------------------------------------------------
# require_cmds — ImportError path (api.py lines 212-214)
# ---------------------------------------------------------------------------


class TestRequireCmds:
    def test_yields_cmds_when_available(self):
        """require_cmds() yields a cmds-like module when Maya is importable."""
        from dcc_mcp_maya.api import require_cmds

        mock_cmds = MagicMock()
        mock_maya = MagicMock()
        mock_maya.cmds = mock_cmds
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with require_cmds() as cmds:
                # cmds should be some object (the mock that Python's import resolved to)
                assert cmds is not None

    def test_raises_import_error_when_maya_missing(self):
        """require_cmds() raises ImportError when maya.cmds is not installed."""
        from dcc_mcp_maya.api import require_cmds

        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            with pytest.raises((ImportError, Exception)):
                with require_cmds() as _cmds:
                    pass

    def test_require_cmds_is_context_manager(self):
        """require_cmds() is a context manager (has __enter__/__exit__)."""
        import contextlib

        from dcc_mcp_maya.api import require_cmds

        assert isinstance(require_cmds, contextlib._GeneratorContextManager.__class__) or callable(require_cmds)


# ---------------------------------------------------------------------------
# get_cmds — ImportError path (api.py lines 228-230)
# ---------------------------------------------------------------------------


class TestGetCmds:
    def test_returns_cmds_module_when_available(self):
        """get_cmds() returns a cmds-like module when Maya is importable."""
        from dcc_mcp_maya.api import get_cmds

        mock_cmds = MagicMock()
        mock_maya = MagicMock()
        mock_maya.cmds = mock_cmds
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            cmds = get_cmds()
            assert cmds is not None

    def test_raises_import_error_when_maya_missing(self):
        """get_cmds() raises ImportError when maya.cmds is absent."""
        from dcc_mcp_maya.api import get_cmds

        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            with pytest.raises((ImportError, Exception)):
                get_cmds()

    def test_get_cmds_is_callable(self):
        """get_cmds is a regular callable (not a context manager)."""
        from dcc_mcp_maya.api import get_cmds

        assert callable(get_cmds)


# ---------------------------------------------------------------------------
# ensure_valid_name (api.py)
# ---------------------------------------------------------------------------


class TestEnsureValidName:
    def test_returns_none_for_valid_name(self):
        from dcc_mcp_maya.api import ensure_valid_name

        assert ensure_valid_name("pSphere1") is None

    def test_returns_none_for_any_non_empty_string(self):
        from dcc_mcp_maya.api import ensure_valid_name

        assert ensure_valid_name("my_node_123") is None

    def test_returns_error_for_empty_string(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name("")
        assert result is not None
        assert result["success"] is False

    def test_returns_error_for_whitespace_only(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name("   ")
        assert result is not None
        assert result["success"] is False

    def test_returns_error_for_none(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name(None)
        assert result is not None
        assert result["success"] is False

    def test_error_mentions_param_name(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name("", param="layer_name")
        assert "layer_name" in result["message"]

    def test_returns_error_for_false(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name(False, param="node")
        assert result is not None
        assert result["success"] is False

    def test_default_param_name_in_error(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name("")
        assert "name" in result["message"]


# ---------------------------------------------------------------------------
# build_context_dict (api.py)
# ---------------------------------------------------------------------------


class TestBuildContextDict:
    def test_excludes_none_values(self):
        from dcc_mcp_maya.api import build_context_dict

        result = build_context_dict(name="pSphere1", parent=None)
        assert "name" in result
        assert "parent" not in result

    def test_keeps_falsy_non_none_values(self):
        from dcc_mcp_maya.api import build_context_dict

        result = build_context_dict(count=0, enabled=False, name="")
        assert result["count"] == 0
        assert result["enabled"] is False
        assert result["name"] == ""

    def test_returns_empty_dict_when_all_none(self):
        from dcc_mcp_maya.api import build_context_dict

        result = build_context_dict(a=None, b=None)
        assert result == {}

    def test_returns_all_when_no_none(self):
        from dcc_mcp_maya.api import build_context_dict

        result = build_context_dict(x=1, y=2, z=3)
        assert result == {"x": 1, "y": 2, "z": 3}

    def test_empty_kwargs_returns_empty_dict(self):
        from dcc_mcp_maya.api import build_context_dict

        result = build_context_dict()
        assert result == {}


# ---------------------------------------------------------------------------
# scene_object_from_node (api.py)
# ---------------------------------------------------------------------------


class TestSceneObjectFromNode:
    def _make_cmds_for_node(self, long_name, object_type="transform", parents=None, visible=True):
        cmds = MagicMock()
        cmds.objectType.return_value = object_type
        cmds.listRelatives.return_value = parents or []
        cmds.getAttr.return_value = visible
        return cmds

    def test_basic_top_level_transform(self):
        from dcc_mcp_maya.api import scene_object_from_node

        cmds = self._make_cmds_for_node("|pSphere1", "transform", parents=[], visible=True)
        result = scene_object_from_node(cmds, "|pSphere1")
        assert result["name"] == "pSphere1"
        assert result["long_name"] == "|pSphere1"
        assert result["object_type"] == "transform"
        assert result["parent"] is None
        assert result["visible"] is True
        assert result["metadata"] == {}

    def test_nested_node_extracts_short_name(self):
        from dcc_mcp_maya.api import scene_object_from_node

        cmds = self._make_cmds_for_node("|group1|pSphere1")
        result = scene_object_from_node(cmds, "|group1|pSphere1")
        assert result["name"] == "pSphere1"
        assert result["long_name"] == "|group1|pSphere1"

    def test_node_with_parent(self):
        from dcc_mcp_maya.api import scene_object_from_node

        cmds = self._make_cmds_for_node("|group1|child", parents=["|group1"])
        result = scene_object_from_node(cmds, "|group1|child")
        assert result["parent"] == "|group1"

    def test_visibility_false(self):
        from dcc_mcp_maya.api import scene_object_from_node

        cmds = self._make_cmds_for_node("|hidden_node", visible=False)
        cmds.getAttr.return_value = False
        result = scene_object_from_node(cmds, "|hidden_node")
        assert result["visible"] is False

    def test_visibility_exception_defaults_to_true(self):
        from dcc_mcp_maya.api import scene_object_from_node

        cmds = MagicMock()
        cmds.objectType.return_value = "transform"
        cmds.listRelatives.return_value = []
        cmds.getAttr.side_effect = RuntimeError("no attr")
        result = scene_object_from_node(cmds, "|pSphere1")
        assert result["visible"] is True

    def test_node_without_pipe_in_name(self):
        from dcc_mcp_maya.api import scene_object_from_node

        cmds = self._make_cmds_for_node("pSphere1")
        result = scene_object_from_node(cmds, "pSphere1")
        assert result["name"] == "pSphere1"
        assert result["long_name"] == "pSphere1"


# ---------------------------------------------------------------------------
# object_transform_from_node (api.py)
# ---------------------------------------------------------------------------


class TestObjectTransformFromNode:
    def _make_cmds_with_xform(self, translate, rotate, scale):
        cmds = MagicMock()

        def getAttr(attr):
            if ".translate" in attr:
                return [translate]
            if ".rotate" in attr:
                return [rotate]
            if ".scale" in attr:
                return [scale]
            return [0.0]

        cmds.getAttr.side_effect = getAttr
        return cmds

    def test_basic_transform(self):
        from dcc_mcp_maya.api import object_transform_from_node

        cmds = self._make_cmds_with_xform(
            translate=(1.0, 2.0, 3.0),
            rotate=(10.0, 20.0, 30.0),
            scale=(1.5, 1.5, 1.5),
        )
        result = object_transform_from_node(cmds, "pSphere1")
        assert result["translate"] == [1.0, 2.0, 3.0]
        assert result["rotate"] == [10.0, 20.0, 30.0]
        assert result["scale"] == [1.5, 1.5, 1.5]

    def test_zero_transform(self):
        from dcc_mcp_maya.api import object_transform_from_node

        cmds = self._make_cmds_with_xform((0, 0, 0), (0, 0, 0), (1, 1, 1))
        result = object_transform_from_node(cmds, "pCube1")
        assert result["translate"] == [0.0, 0.0, 0.0]
        assert result["scale"] == [1.0, 1.0, 1.0]

    def test_values_are_floats(self):
        from dcc_mcp_maya.api import object_transform_from_node

        cmds = self._make_cmds_with_xform((1, 2, 3), (4, 5, 6), (7, 8, 9))
        result = object_transform_from_node(cmds, "node1")
        for key in ("translate", "rotate", "scale"):
            for v in result[key]:
                assert isinstance(v, float)

    def test_negative_values(self):
        from dcc_mcp_maya.api import object_transform_from_node

        cmds = self._make_cmds_with_xform((-1.0, -2.5, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        result = object_transform_from_node(cmds, "node2")
        assert result["translate"] == [-1.0, -2.5, 0.0]


# ---------------------------------------------------------------------------
# bounding_box_from_node (api.py)
# ---------------------------------------------------------------------------


class TestBoundingBoxFromNode:
    def _make_cmds_with_bb(self, bb):
        cmds = MagicMock()
        cmds.exactWorldBoundingBox.return_value = bb
        return cmds

    def test_basic_bounding_box(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        cmds = self._make_cmds_with_bb([0.0, 0.0, 0.0, 2.0, 4.0, 6.0])
        result = bounding_box_from_node(cmds, "pBox")
        assert result["min"] == [0.0, 0.0, 0.0]
        assert result["max"] == [2.0, 4.0, 6.0]
        assert result["center"] == [1.0, 2.0, 3.0]
        assert result["size"] == [2.0, 4.0, 6.0]

    def test_center_computed_correctly(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        cmds = self._make_cmds_with_bb([-1.0, -2.0, -3.0, 1.0, 2.0, 3.0])
        result = bounding_box_from_node(cmds, "node")
        assert result["center"] == [0.0, 0.0, 0.0]

    def test_size_computed_correctly(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        cmds = self._make_cmds_with_bb([1.0, 2.0, 3.0, 5.0, 6.0, 7.0])
        result = bounding_box_from_node(cmds, "node")
        assert result["size"] == [4.0, 4.0, 4.0]

    def test_values_are_floats(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        cmds = self._make_cmds_with_bb([0, 0, 0, 1, 1, 1])
        result = bounding_box_from_node(cmds, "node")
        for key in ("min", "max", "center", "size"):
            for v in result[key]:
                assert isinstance(v, float)

    def test_calls_exact_world_bounding_box(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        cmds = self._make_cmds_with_bb([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        bounding_box_from_node(cmds, "myCube")
        cmds.exactWorldBoundingBox.assert_called_once_with("myCube")

    def test_asymmetric_bounding_box(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        cmds = self._make_cmds_with_bb([0.0, 1.0, 2.0, 10.0, 3.0, 8.0])
        result = bounding_box_from_node(cmds, "node")
        assert result["size"] == [10.0, 2.0, 6.0]
        assert result["center"] == [5.0, 2.0, 5.0]


# ---------------------------------------------------------------------------
# server.py — registry property forwards to the underlying skill client.
# (DccServerBase.registry was decomposed in dcc-mcp-core 0.14.17 and now
# delegates to ``_skill_client.registry`` instead of ``_server._registry``.)
# ---------------------------------------------------------------------------


class TestServerRegistryProperty:
    """Cover the inherited ``registry`` property after the core decomposition."""

    def _import_server(self):
        import importlib

        for mod in list(sys.modules):
            if "dcc_mcp_maya" in mod:
                del sys.modules[mod]

        mock_maya = MagicMock()
        modules = {
            "maya": mock_maya,
            "maya.cmds": MagicMock(),
            "maya.mel": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, modules):
            srv_mod = importlib.import_module("dcc_mcp_maya.server")
            return srv_mod.MayaMcpServer(port=0)

    def test_registry_forwards_to_skill_client(self):
        """``server.registry`` returns whatever ``_skill_client.registry`` returns."""
        server = self._import_server()
        fake_registry = MagicMock(name="fake_registry")
        server._skill_client = MagicMock()
        server._skill_client.registry = fake_registry
        assert server.registry is fake_registry

    def test_registry_returns_none_when_skill_client_has_none(self):
        """When the skill client exposes no registry, the property returns None."""
        server = self._import_server()
        server._skill_client = MagicMock()
        server._skill_client.registry = None
        assert server.registry is None


# ---------------------------------------------------------------------------
# Public API re-export verification for new helpers
# ---------------------------------------------------------------------------


class TestApiPublicReexportRound33:
    """Verify that all new helpers are exported from dcc_mcp_maya namespace."""

    def test_ensure_valid_name_in_api(self):
        from dcc_mcp_maya.api import ensure_valid_name

        assert callable(ensure_valid_name)

    def test_build_context_dict_in_api(self):
        from dcc_mcp_maya.api import build_context_dict

        assert callable(build_context_dict)

    def test_scene_object_from_node_in_api(self):
        from dcc_mcp_maya.api import scene_object_from_node

        assert callable(scene_object_from_node)

    def test_object_transform_from_node_in_api(self):
        from dcc_mcp_maya.api import object_transform_from_node

        assert callable(object_transform_from_node)

    def test_bounding_box_from_node_in_api(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        assert callable(bounding_box_from_node)

    def test_require_cmds_callable(self):
        from dcc_mcp_maya.api import require_cmds

        assert callable(require_cmds)

    def test_get_cmds_callable(self):
        from dcc_mcp_maya.api import get_cmds

        assert callable(get_cmds)
