"""Round 39 tests: Cross-DCC data model helpers + server bind_and_register/search_skills.

Covers:
- dcc_mcp_maya.api: scene_object_from_node, object_transform_from_node, bounding_box_from_node
- server.py: search_skills, bind_and_register, find_best_service, rank_services
- maya-scene/get_scene_info.py  (uses scene_object_from_node)
- maya-scene/get_bounding_box.py  (uses bounding_box_from_node)
- dcc_mcp_maya.__init__ re-exports for the new helpers
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_cmds(
    obj_exists=True,
    obj_type="transform",
    translate=(1.0, 2.0, 3.0),
    rotate=(10.0, 20.0, 30.0),
    scale=(1.0, 1.0, 1.0),
    bbox=(-1.0, -2.0, -3.0, 1.0, 2.0, 3.0),
    visibility=True,
    list_relatives_parent=None,
    list_relatives_children=None,
):
    """Return a MagicMock maya.cmds with sensible defaults."""
    cmds = MagicMock()
    cmds.objExists.return_value = obj_exists
    cmds.objectType.return_value = obj_type
    cmds.getAttr.side_effect = lambda attr: {
        ".translate": [list(translate)],
        ".rotate": [list(rotate)],
        ".scale": [list(scale)],
        ".visibility": visibility,
    }.get(attr.split("|")[-1].split(".", 1)[-1] if "." in attr else None, [list(translate)])

    def _getAttr(attr):
        if attr.endswith(".translate"):
            return [list(translate)]
        if attr.endswith(".rotate"):
            return [list(rotate)]
        if attr.endswith(".scale"):
            return [list(scale)]
        if attr.endswith(".visibility"):
            return visibility
        return [list(translate)]

    cmds.getAttr.side_effect = _getAttr
    cmds.exactWorldBoundingBox.return_value = list(bbox)
    cmds.listRelatives.side_effect = lambda node, **kw: (
        list_relatives_parent if kw.get("parent") else list_relatives_children or []
    )
    return cmds


def _load_skill(rel_path, mock_cmds, func_name="main", **kwargs):
    """Import a skill module under a unique name and call func_name(**kwargs)."""
    import importlib.util
    import os

    skill_root = os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "dcc_mcp_maya",
        "skills",
    )
    full_path = os.path.normpath(os.path.join(skill_root, rel_path))
    module_name = "skill_r39_{}".format(abs(hash(full_path)))

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    with patch.dict(
        sys.modules,
        {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.mel": MagicMock(),
            "maya.utils": MagicMock(),
        },
    ):
        spec = importlib.util.spec_from_file_location(module_name, full_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


# ---------------------------------------------------------------------------
# TestSceneObjectFromNode
# ---------------------------------------------------------------------------


class TestSceneObjectFromNode:
    """Tests for dcc_mcp_maya.api.scene_object_from_node."""

    def _call(self, cmds):
        from dcc_mcp_maya.api import scene_object_from_node

        return scene_object_from_node(cmds, "|group1|pSphere1")

    def test_name_extracted_from_long_name(self):
        cmds = _make_cmds(list_relatives_parent=None)
        result = self._call(cmds)
        assert result["name"] == "pSphere1"

    def test_long_name_preserved(self):
        cmds = _make_cmds()
        result = self._call(cmds)
        assert result["long_name"] == "|group1|pSphere1"

    def test_object_type(self):
        cmds = _make_cmds(obj_type="mesh")
        result = self._call(cmds)
        assert result["object_type"] == "mesh"

    def test_parent_from_list_relatives(self):
        cmds = _make_cmds(list_relatives_parent=["|group1"])
        result = self._call(cmds)
        assert result["parent"] == "|group1"

    def test_parent_none_when_no_parent(self):
        cmds = _make_cmds(list_relatives_parent=[])
        result = self._call(cmds)
        assert result["parent"] is None

    def test_visible_true(self):
        cmds = _make_cmds(visibility=True)
        result = self._call(cmds)
        assert result["visible"] is True

    def test_visible_false(self):
        cmds = _make_cmds(visibility=False)
        result = self._call(cmds)
        assert result["visible"] is False

    def test_metadata_empty_dict(self):
        cmds = _make_cmds()
        result = self._call(cmds)
        assert result["metadata"] == {}

    def test_visible_defaults_true_on_getattr_exception(self):
        from dcc_mcp_maya.api import scene_object_from_node

        cmds = MagicMock()
        cmds.objectType.return_value = "transform"
        cmds.listRelatives.return_value = []
        cmds.getAttr.side_effect = RuntimeError("no visibility attr")
        result = scene_object_from_node(cmds, "pSphere1")
        assert result["visible"] is True


# ---------------------------------------------------------------------------
# TestObjectTransformFromNode
# ---------------------------------------------------------------------------


class TestObjectTransformFromNode:
    """Tests for dcc_mcp_maya.api.object_transform_from_node."""

    def _call(self, cmds):
        from dcc_mcp_maya.api import object_transform_from_node

        return object_transform_from_node(cmds, "pSphere1")

    def test_translate_values(self):
        cmds = _make_cmds(translate=(1.0, 2.0, 3.0))
        result = self._call(cmds)
        assert result["translate"] == [1.0, 2.0, 3.0]

    def test_rotate_values(self):
        cmds = _make_cmds(rotate=(45.0, 0.0, 90.0))
        result = self._call(cmds)
        assert result["rotate"] == [45.0, 0.0, 90.0]

    def test_scale_values(self):
        cmds = _make_cmds(scale=(2.0, 3.0, 0.5))
        result = self._call(cmds)
        assert result["scale"] == [2.0, 3.0, 0.5]

    def test_keys_present(self):
        cmds = _make_cmds()
        result = self._call(cmds)
        assert set(result.keys()) == {"translate", "rotate", "scale"}

    def test_all_floats(self):
        cmds = _make_cmds(translate=(0.0, 0.0, 0.0))
        result = self._call(cmds)
        assert all(isinstance(v, float) for v in result["translate"])


# ---------------------------------------------------------------------------
# TestBoundingBoxFromNode
# ---------------------------------------------------------------------------


class TestBoundingBoxFromNode:
    """Tests for dcc_mcp_maya.api.bounding_box_from_node."""

    def _call(self, cmds):
        from dcc_mcp_maya.api import bounding_box_from_node

        return bounding_box_from_node(cmds, "pSphere1")

    def test_min_values(self):
        cmds = _make_cmds(bbox=(-1.0, -2.0, -3.0, 1.0, 2.0, 3.0))
        result = self._call(cmds)
        assert result["min"] == [-1.0, -2.0, -3.0]

    def test_max_values(self):
        cmds = _make_cmds(bbox=(-1.0, -2.0, -3.0, 1.0, 2.0, 3.0))
        result = self._call(cmds)
        assert result["max"] == [1.0, 2.0, 3.0]

    def test_center_computed(self):
        cmds = _make_cmds(bbox=(-2.0, -4.0, -6.0, 2.0, 4.0, 6.0))
        result = self._call(cmds)
        assert result["center"] == [0.0, 0.0, 0.0]

    def test_size_computed(self):
        cmds = _make_cmds(bbox=(0.0, 0.0, 0.0, 4.0, 6.0, 8.0))
        result = self._call(cmds)
        assert result["size"] == [4.0, 6.0, 8.0]

    def test_asymmetric_bbox(self):
        cmds = _make_cmds(bbox=(1.0, 2.0, 3.0, 5.0, 8.0, 11.0))
        result = self._call(cmds)
        assert result["center"] == [3.0, 5.0, 7.0]
        assert result["size"] == [4.0, 6.0, 8.0]


# ---------------------------------------------------------------------------
# TestGetSceneInfoCrossModel
# ---------------------------------------------------------------------------


class TestGetSceneInfoCrossModel:
    """get_scene_info.py now uses scene_object_from_node + object_transform_from_node."""

    def _make_scene_cmds(self):
        cmds = MagicMock()
        cmds.ls.return_value = ["|pSphere1", "|pCube1"]
        cmds.objectType.return_value = "transform"

        def _getAttr(attr):
            if attr.endswith(".translate"):
                return [(1.0, 0.0, 0.0)]
            if attr.endswith(".rotate"):
                return [(0.0, 45.0, 0.0)]
            if attr.endswith(".scale"):
                return [(1.0, 1.0, 1.0)]
            if attr.endswith(".visibility"):
                return True
            return [(0.0, 0.0, 0.0)]

        cmds.getAttr.side_effect = _getAttr
        cmds.listRelatives.side_effect = lambda node, **kw: [] if kw.get("parent") else []
        return cmds

    def test_returns_success(self):
        cmds = self._make_scene_cmds()
        result = _load_skill("maya-scene/scripts/get_scene_info.py", cmds)
        assert result["success"] is True

    def test_count_matches_transforms(self):
        cmds = self._make_scene_cmds()
        result = _load_skill("maya-scene/scripts/get_scene_info.py", cmds)
        assert result["context"]["count"] == 2

    def test_node_has_scene_object_fields(self):
        cmds = self._make_scene_cmds()
        result = _load_skill("maya-scene/scripts/get_scene_info.py", cmds)
        node = result["context"]["nodes"][0]
        # scene_object_from_node fields
        assert "name" in node
        assert "long_name" in node
        assert "object_type" in node
        assert "parent" in node
        assert "visible" in node

    def test_node_has_transform_fields_by_default(self):
        cmds = self._make_scene_cmds()
        result = _load_skill("maya-scene/scripts/get_scene_info.py", cmds)
        node = result["context"]["nodes"][0]
        assert "translate" in node
        assert "rotate" in node
        assert "scale" in node

    def test_no_transform_fields_when_disabled(self):
        cmds = self._make_scene_cmds()
        result = _load_skill("maya-scene/scripts/get_scene_info.py", cmds, include_transforms=False)
        node = result["context"]["nodes"][0]
        assert "translate" not in node

    def test_prompt_present(self):
        cmds = self._make_scene_cmds()
        result = _load_skill("maya-scene/scripts/get_scene_info.py", cmds)
        assert result.get("prompt")

    def test_name_short_from_long(self):
        cmds = self._make_scene_cmds()
        result = _load_skill("maya-scene/scripts/get_scene_info.py", cmds)
        node = result["context"]["nodes"][0]
        # long_name is "|pSphere1", name should be "pSphere1"
        assert "|" not in node["name"]


# ---------------------------------------------------------------------------
# TestGetBoundingBoxCrossModel
# ---------------------------------------------------------------------------


class TestGetBoundingBoxCrossModel:
    """get_bounding_box.py now uses bounding_box_from_node."""

    def test_success_returns_bbox_fields(self):
        cmds = _make_cmds(obj_exists=True, bbox=(-1.0, -1.0, -1.0, 1.0, 1.0, 1.0))
        result = _load_skill("maya-scene/scripts/get_bounding_box.py", cmds, object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["min"] == [-1.0, -1.0, -1.0]
        assert result["context"]["max"] == [1.0, 1.0, 1.0]
        assert result["context"]["center"] == [0.0, 0.0, 0.0]
        assert result["context"]["size"] == [2.0, 2.0, 2.0]

    def test_missing_node_returns_error(self):
        cmds = _make_cmds(obj_exists=False)
        result = _load_skill("maya-scene/scripts/get_bounding_box.py", cmds, object_name="missing")
        assert result["success"] is False

    def test_asymmetric_bbox(self):
        cmds = _make_cmds(obj_exists=True, bbox=(0.0, 0.0, 0.0, 6.0, 4.0, 2.0))
        result = _load_skill("maya-scene/scripts/get_bounding_box.py", cmds, object_name="pBox1")
        assert result["context"]["size"] == [6.0, 4.0, 2.0]
        assert result["context"]["center"] == [3.0, 2.0, 1.0]

    def test_prompt_present(self):
        cmds = _make_cmds(obj_exists=True)
        result = _load_skill("maya-scene/scripts/get_bounding_box.py", cmds, object_name="pSphere1")
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestServerFindSkills
# ---------------------------------------------------------------------------


class TestServerFindSkills:
    """server.MayaMcpServer.search_skills wraps DccServerBase.search_skills (v0.14.0+)."""

    def _make_server(self, catalog_server=None):
        from dcc_mcp_maya.server import MayaMcpServer

        server = object.__new__(MayaMcpServer)
        server._dcc_name = "maya"
        server._config = MagicMock()
        server._handle = None
        server._server = catalog_server or MagicMock()
        return server

    def test_method_exists(self):
        server = self._make_server()
        assert hasattr(server, "search_skills")
        assert callable(server.search_skills)

    def test_delegates_to_catalog_search_skills(self):
        mock_catalog = MagicMock()
        mock_catalog.search_skills.return_value = ["skill_a", "skill_b"]
        server = self._make_server(mock_catalog)
        result = server.search_skills(query="scene", tags=["create"], dcc="maya")
        call_args, call_kwargs = mock_catalog.search_skills.call_args
        if call_kwargs:
            assert call_kwargs["query"] == "scene"
            assert call_kwargs["tags"] == ["create"]
            assert call_kwargs["dcc"] == "maya"
        else:
            assert call_args[0] == "scene"
            assert call_args[1] == ["create"]
            assert call_args[2] == "maya"
        assert result == ["skill_a", "skill_b"]

    def test_returns_empty_list_on_exception(self):
        mock_catalog = MagicMock()
        mock_catalog.search_skills.side_effect = RuntimeError("catalog error")
        server = self._make_server(mock_catalog)
        result = server.search_skills(query="something")
        assert result == []

    def test_returns_list_type(self):
        mock_catalog = MagicMock()
        mock_catalog.search_skills.return_value = iter(["a", "b"])
        server = self._make_server(mock_catalog)
        result = server.search_skills()
        assert isinstance(result, list)

    def test_no_args_passes_none_defaults(self):
        mock_catalog = MagicMock()
        mock_catalog.search_skills.return_value = []
        server = self._make_server(mock_catalog)
        server.search_skills()
        mock_catalog.search_skills.assert_called_once()
        call_args, call_kwargs = mock_catalog.search_skills.call_args
        if call_kwargs:
            assert call_kwargs.get("query") is None
            assert call_kwargs.get("dcc") is None
        else:
            assert call_args[0] is None
            assert call_args[2] is None


# ---------------------------------------------------------------------------
# TestServerBindAndRegister
# ---------------------------------------------------------------------------


class TestServerBindAndRegister:
    """server.MayaMcpServer.bind_and_register wraps TransportManager.bind_and_register."""

    def _make_server(self):
        from dcc_mcp_maya.server import MayaMcpServer

        server = object.__new__(MayaMcpServer)
        server._dcc_name = "maya"
        server._config = MagicMock()
        server._handle = None
        server._server = MagicMock()
        return server

    def test_method_exists(self):
        server = self._make_server()
        assert hasattr(server, "bind_and_register")

    def test_delegates_to_transport_manager(self):
        server = self._make_server()
        mgr = MagicMock()
        mgr.bind_and_register.return_value = ("instance-1", MagicMock())
        result = server.bind_and_register(mgr, version="2025")
        mgr.bind_and_register.assert_called_once_with("maya", version="2025", metadata={})
        assert result[0] == "instance-1"

    def test_returns_none_on_exception(self):
        server = self._make_server()
        mgr = MagicMock()
        mgr.bind_and_register.side_effect = RuntimeError("transport error")
        result = server.bind_and_register(mgr, version="2025")
        assert result is None

    def test_auto_detects_version_fallback_when_maya_unavailable(self):
        """When maya.cmds is not importable, version falls back to 'unknown'."""
        server = self._make_server()
        mgr = MagicMock()
        mgr.bind_and_register.return_value = ("inst", MagicMock())

        # Temporarily remove maya from sys.modules so import fails
        saved = {k: v for k, v in sys.modules.items() if k.startswith("maya")}
        for k in list(saved):
            sys.modules.pop(k, None)
        try:
            server.bind_and_register(mgr)
        finally:
            sys.modules.update(saved)

        call_kwargs = mgr.bind_and_register.call_args
        assert call_kwargs[1]["version"] == "unknown"

    def test_custom_metadata_forwarded(self):
        server = self._make_server()
        mgr = MagicMock()
        mgr.bind_and_register.return_value = ("inst", MagicMock())
        server.bind_and_register(mgr, version="2025", metadata={"artist": "alice"})
        mgr.bind_and_register.assert_called_once_with("maya", version="2025", metadata={"artist": "alice"})


# ---------------------------------------------------------------------------
# TestServerFindBestService
# ---------------------------------------------------------------------------


class TestServerFindBestService:
    """server.MayaMcpServer.find_best_service is a static method."""

    def test_method_exists(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "find_best_service")

    def test_delegates_to_transport_manager(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mgr = MagicMock()
        mock_service = MagicMock()
        mgr.find_best_service.return_value = mock_service
        result = MayaMcpServer.find_best_service(mgr, dcc_type="maya")
        mgr.find_best_service.assert_called_once_with("maya")
        assert result is mock_service

    def test_default_dcc_type_is_maya(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mgr = MagicMock()
        mgr.find_best_service.return_value = None
        MayaMcpServer.find_best_service(mgr)
        mgr.find_best_service.assert_called_once_with("maya")

    def test_returns_none_on_exception(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mgr = MagicMock()
        mgr.find_best_service.side_effect = RuntimeError("no service")
        result = MayaMcpServer.find_best_service(mgr)
        assert result is None


# ---------------------------------------------------------------------------
# TestServerRankServices
# ---------------------------------------------------------------------------


class TestServerRankServices:
    """server.MayaMcpServer.rank_services is a static method."""

    def test_method_exists(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "rank_services")

    def test_delegates_to_transport_manager(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mgr = MagicMock()
        mgr.rank_services.return_value = ["svc1", "svc2"]
        result = MayaMcpServer.rank_services(mgr, dcc_type="maya")
        mgr.rank_services.assert_called_once_with("maya")
        assert result == ["svc1", "svc2"]

    def test_default_dcc_type_is_maya(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mgr = MagicMock()
        mgr.rank_services.return_value = []
        MayaMcpServer.rank_services(mgr)
        mgr.rank_services.assert_called_once_with("maya")

    def test_returns_empty_list_on_exception(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mgr = MagicMock()
        mgr.rank_services.side_effect = RuntimeError("registry error")
        result = MayaMcpServer.rank_services(mgr)
        assert result == []

    def test_result_is_list(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mgr = MagicMock()
        mgr.rank_services.return_value = iter(["a", "b"])
        result = MayaMcpServer.rank_services(mgr)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# TestCrossDccModelReexports
# ---------------------------------------------------------------------------


class TestCrossDccModelReexports:
    """The new helpers are accessible from the top-level dcc_mcp_maya package."""

    def test_scene_object_from_node_importable(self):
        from dcc_mcp_maya import scene_object_from_node

        assert callable(scene_object_from_node)

    def test_object_transform_from_node_importable(self):
        from dcc_mcp_maya import object_transform_from_node

        assert callable(object_transform_from_node)

    def test_bounding_box_from_node_importable(self):
        from dcc_mcp_maya import bounding_box_from_node

        assert callable(bounding_box_from_node)

    def test_in_package_all(self):
        import dcc_mcp_maya

        for name in ("scene_object_from_node", "object_transform_from_node", "bounding_box_from_node"):
            assert name in dcc_mcp_maya.__all__, "{} not in __all__".format(name)

    def test_in_api_all(self):
        from dcc_mcp_maya import api

        for name in ("scene_object_from_node", "object_transform_from_node", "bounding_box_from_node"):
            assert name in api.__all__, "{} not in api.__all__".format(name)
