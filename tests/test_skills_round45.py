"""Round 45 tests: server.py SkillCatalog + search API coverage.

Tests cover:
1. MayaMcpServer.search_skills() — wraps ActionRegistry.search_actions
2. MayaMcpServer.unregister_skill() — wraps ActionRegistry.unregister
3. MayaMcpServer.find_skills() — wraps SkillCatalog.find_skills
4. MayaMcpServer.get_skill_categories() — wraps ActionRegistry.get_categories
5. MayaMcpServer.get_skill_tags() — wraps ActionRegistry.get_tags
6. MayaMcpServer.rank_services() — wraps TransportManager.rank_services
7. MayaMcpServer.find_best_service() — wraps TransportManager.find_best_service
8. MayaMcpServer.is_skill_loaded() — wraps SkillCatalog.is_loaded
9. MayaMcpServer.get_skill_info() — wraps SkillCatalog.get_skill_info
10. Structural: all helpers present in server module
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_server():
    """Create MayaMcpServer with a fully mocked dcc_mcp_core."""
    mock_core = MagicMock()
    mock_server_inst = MagicMock()
    mock_core.create_skill_manager.return_value = mock_server_inst
    mock_core.McpHttpConfig.return_value = MagicMock()

    with patch.dict(sys.modules, {"dcc_mcp_core": mock_core}):
        for mod in [k for k in sys.modules if "dcc_mcp_maya" in k]:
            del sys.modules[mod]
        import importlib

        server_mod = importlib.import_module("dcc_mcp_maya.server")
        server = server_mod.MayaMcpServer(port=19900)

    server._mock_core = mock_core
    server._mock_inst = mock_server_inst
    return server


def _make_server_with_registry():
    """Create server + inject a mock ActionRegistry via _registry attr."""
    server = _make_server()
    mock_registry = MagicMock()
    # Expose registry via the internal _registry attr used by server.registry property
    server._mock_inst._registry = mock_registry
    server._server = server._mock_inst
    return server, mock_registry


# ---------------------------------------------------------------------------
# 1. search_skills
# ---------------------------------------------------------------------------


class TestSearchSkills:
    def test_returns_list_from_search_actions(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.return_value = [{"name": "maya_scene__create_object"}]
        result = server.search_skills(category="geometry")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_default_dcc_name_is_maya(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.return_value = []
        server.search_skills(category="mesh")
        call_kwargs = reg.search_actions.call_args
        assert call_kwargs[1].get("dcc_name") == "maya"

    def test_explicit_dcc_name_is_forwarded(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.return_value = []
        server.search_skills(dcc_name="houdini")
        call_kwargs = reg.search_actions.call_args
        assert call_kwargs[1].get("dcc_name") == "houdini"

    def test_tags_forwarded(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.return_value = []
        server.search_skills(tags=["rigging", "ik"])
        call_kwargs = reg.search_actions.call_args
        assert call_kwargs[1].get("tags") == ["rigging", "ik"]

    def test_returns_empty_when_registry_none(self):
        server = _make_server()
        server._server._registry = None
        result = server.search_skills()
        assert result == []

    def test_returns_empty_on_exception(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.side_effect = RuntimeError("boom")
        result = server.search_skills(category="x")
        assert result == []

    def test_returns_empty_when_no_registry_attr(self):
        server = _make_server()
        # _registry attribute does not exist at all
        del server._server._registry
        result = server.search_skills()
        assert result == []


# ---------------------------------------------------------------------------
# 2. unregister_skill
# ---------------------------------------------------------------------------


class TestUnregisterSkill:
    def test_calls_registry_unregister(self):
        server, reg = _make_server_with_registry()
        server.unregister_skill("maya_scene__create_object")
        reg.unregister.assert_called_once_with("maya_scene__create_object", dcc_name=None)

    def test_forwards_dcc_name(self):
        server, reg = _make_server_with_registry()
        server.unregister_skill("maya_scene__delete_object", dcc_name="maya")
        reg.unregister.assert_called_once_with("maya_scene__delete_object", dcc_name="maya")

    def test_silently_ignores_exception(self):
        server, reg = _make_server_with_registry()
        reg.unregister.side_effect = KeyError("not found")
        # Should not raise
        server.unregister_skill("nonexistent_skill")

    def test_does_nothing_when_registry_none(self):
        server = _make_server()
        server._server._registry = None
        # Should not raise
        server.unregister_skill("some_skill")

    def test_does_nothing_when_no_registry_attr(self):
        server = _make_server()
        del server._server._registry
        server.unregister_skill("some_skill")


# ---------------------------------------------------------------------------
# 3. find_skills (SkillCatalog.find_skills)
# ---------------------------------------------------------------------------


class TestFindSkills:
    def test_returns_list(self):
        server = _make_server()
        mock_summary = MagicMock()
        mock_summary.name = "maya-scene"
        server._server.find_skills.return_value = [mock_summary]
        result = server.find_skills(query="scene")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_forwards_query_tags_dcc(self):
        server = _make_server()
        server._server.find_skills.return_value = []
        server.find_skills(query="bounding", tags=["mesh"], dcc="maya")
        server._server.find_skills.assert_called_once_with(query="bounding", tags=["mesh"], dcc="maya")

    def test_returns_empty_on_exception(self):
        server = _make_server()
        server._server.find_skills.side_effect = AttributeError("no catalog")
        result = server.find_skills(query="x")
        assert result == []

    def test_none_args_forwarded(self):
        server = _make_server()
        server._server.find_skills.return_value = []
        server.find_skills()
        server._server.find_skills.assert_called_once_with(query=None, tags=None, dcc=None)


# ---------------------------------------------------------------------------
# 4. get_skill_categories
# ---------------------------------------------------------------------------


class TestGetSkillCategories:
    def test_returns_sorted_list(self):
        server, reg = _make_server_with_registry()
        reg.get_categories.return_value = ["rigging", "animation", "geometry"]
        result = server.get_skill_categories()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_returns_empty_on_exception(self):
        server, reg = _make_server_with_registry()
        reg.get_categories.side_effect = AttributeError("missing")
        result = server.get_skill_categories()
        assert result == []

    def test_returns_empty_when_registry_none(self):
        server = _make_server()
        server._server._registry = None
        assert server.get_skill_categories() == []


# ---------------------------------------------------------------------------
# 5. get_skill_tags
# ---------------------------------------------------------------------------


class TestGetSkillTags:
    def test_returns_list(self):
        server, reg = _make_server_with_registry()
        reg.get_tags.return_value = ["mesh", "create", "scene"]
        result = server.get_skill_tags()
        assert isinstance(result, list)

    def test_default_dcc_is_maya(self):
        server, reg = _make_server_with_registry()
        reg.get_tags.return_value = []
        server.get_skill_tags()
        call_kwargs = reg.get_tags.call_args
        assert call_kwargs[1].get("dcc_name") == "maya"

    def test_explicit_dcc_forwarded(self):
        server, reg = _make_server_with_registry()
        reg.get_tags.return_value = []
        server.get_skill_tags(dcc_name="blender")
        call_kwargs = reg.get_tags.call_args
        assert call_kwargs[1].get("dcc_name") == "blender"

    def test_returns_empty_on_exception(self):
        server, reg = _make_server_with_registry()
        reg.get_tags.side_effect = AttributeError("missing")
        result = server.get_skill_tags()
        assert result == []

    def test_returns_empty_when_registry_none(self):
        server = _make_server()
        server._server._registry = None
        assert server.get_skill_tags() == []


# ---------------------------------------------------------------------------
# 6. rank_services (static method)
# ---------------------------------------------------------------------------


class TestRankServices:
    def test_returns_list_from_transport_manager(self):
        server = _make_server()
        mock_tm = MagicMock()
        mock_tm.rank_services.return_value = [MagicMock(), MagicMock()]
        result = server.rank_services(mock_tm)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_default_dcc_type_is_maya(self):
        server = _make_server()
        mock_tm = MagicMock()
        mock_tm.rank_services.return_value = []
        server.rank_services(mock_tm)
        mock_tm.rank_services.assert_called_once_with("maya")

    def test_explicit_dcc_type_forwarded(self):
        mock_tm = MagicMock()
        mock_tm.rank_services.return_value = []
        import importlib

        with patch.dict(sys.modules, {"dcc_mcp_core": MagicMock()}):
            server_mod = importlib.import_module("dcc_mcp_maya.server")
        server_mod.MayaMcpServer.rank_services(mock_tm, dcc_type="houdini")
        mock_tm.rank_services.assert_called_with("houdini")

    def test_returns_empty_on_exception(self):
        server = _make_server()
        mock_tm = MagicMock()
        mock_tm.rank_services.side_effect = RuntimeError("unreachable")
        result = server.rank_services(mock_tm)
        assert result == []


# ---------------------------------------------------------------------------
# 7. find_best_service (static method)
# ---------------------------------------------------------------------------


class TestFindBestService:
    def test_returns_service_from_transport_manager(self):
        server = _make_server()
        mock_tm = MagicMock()
        fake_service = MagicMock()
        mock_tm.find_best_service.return_value = fake_service
        result = server.find_best_service(mock_tm)
        assert result is fake_service

    def test_default_dcc_type_is_maya(self):
        server = _make_server()
        mock_tm = MagicMock()
        mock_tm.find_best_service.return_value = None
        server.find_best_service(mock_tm)
        mock_tm.find_best_service.assert_called_once_with("maya")

    def test_explicit_dcc_type_forwarded(self):
        server = _make_server()
        mock_tm = MagicMock()
        mock_tm.find_best_service.return_value = None
        server.find_best_service(mock_tm, dcc_type="blender")
        mock_tm.find_best_service.assert_called_once_with("blender")

    def test_returns_none_on_exception(self):
        server = _make_server()
        mock_tm = MagicMock()
        mock_tm.find_best_service.side_effect = ConnectionError("no service")
        result = server.find_best_service(mock_tm)
        assert result is None


# ---------------------------------------------------------------------------
# 8. is_skill_loaded
# ---------------------------------------------------------------------------


class TestIsSkillLoaded:
    def test_returns_true_when_loaded(self):
        server = _make_server()
        server._server.is_loaded.return_value = True
        assert server.is_skill_loaded("maya-scene") is True

    def test_returns_false_when_not_loaded(self):
        server = _make_server()
        server._server.is_loaded.return_value = False
        assert server.is_skill_loaded("maya-nonexistent") is False

    def test_forwarded_name_to_is_loaded(self):
        server = _make_server()
        server._server.is_loaded.return_value = True
        server.is_skill_loaded("maya-rigging")
        server._server.is_loaded.assert_called_once_with("maya-rigging")

    def test_returns_false_on_exception(self):
        server = _make_server()
        server._server.is_loaded.side_effect = AttributeError("no catalog")
        assert server.is_skill_loaded("maya-scene") is False

    def test_truthy_return_coerced_to_bool(self):
        server = _make_server()
        # is_loaded returns a truthy non-bool
        server._server.is_loaded.return_value = 1
        result = server.is_skill_loaded("maya-animation")
        assert isinstance(result, bool)
        assert result is True


# ---------------------------------------------------------------------------
# 9. get_skill_info
# ---------------------------------------------------------------------------


class TestGetSkillInfo:
    def test_returns_metadata_object(self):
        server = _make_server()
        fake_meta = MagicMock()
        fake_meta.name = "maya-scene"
        fake_meta.description = "Scene operations"
        server._server.get_skill_info.return_value = fake_meta
        result = server.get_skill_info("maya-scene")
        assert result is fake_meta

    def test_returns_none_for_unknown_skill(self):
        server = _make_server()
        server._server.get_skill_info.return_value = None
        result = server.get_skill_info("nonexistent")
        assert result is None

    def test_name_forwarded(self):
        server = _make_server()
        server._server.get_skill_info.return_value = None
        server.get_skill_info("maya-animation")
        server._server.get_skill_info.assert_called_once_with("maya-animation")

    def test_returns_none_on_exception(self):
        server = _make_server()
        server._server.get_skill_info.side_effect = KeyError("not found")
        result = server.get_skill_info("maya-scene")
        assert result is None

    def test_metadata_description_accessible(self):
        server = _make_server()
        meta = MagicMock()
        meta.description = "Manages Maya scenes"
        server._server.get_skill_info.return_value = meta
        info = server.get_skill_info("maya-scene")
        assert info.description == "Manages Maya scenes"


# ---------------------------------------------------------------------------
# 10. Structural: all new helpers present in server module
# ---------------------------------------------------------------------------


class TestServerStructural:
    def test_is_skill_loaded_in_server_class(self):
        import importlib

        with patch.dict(sys.modules, {"dcc_mcp_core": MagicMock()}):
            for mod in [k for k in sys.modules if "dcc_mcp_maya" in k]:
                del sys.modules[mod]
            server_mod = importlib.import_module("dcc_mcp_maya.server")
        assert hasattr(server_mod.MayaMcpServer, "is_skill_loaded")

    def test_get_skill_info_in_server_class(self):
        import importlib

        with patch.dict(sys.modules, {"dcc_mcp_core": MagicMock()}):
            for mod in [k for k in sys.modules if "dcc_mcp_maya" in k]:
                del sys.modules[mod]
            server_mod = importlib.import_module("dcc_mcp_maya.server")
        assert hasattr(server_mod.MayaMcpServer, "get_skill_info")

    def test_search_skills_in_server_class(self):
        import importlib

        with patch.dict(sys.modules, {"dcc_mcp_core": MagicMock()}):
            for mod in [k for k in sys.modules if "dcc_mcp_maya" in k]:
                del sys.modules[mod]
            server_mod = importlib.import_module("dcc_mcp_maya.server")
        assert hasattr(server_mod.MayaMcpServer, "search_skills")

    def test_find_skills_in_server_class(self):
        import importlib

        with patch.dict(sys.modules, {"dcc_mcp_core": MagicMock()}):
            for mod in [k for k in sys.modules if "dcc_mcp_maya" in k]:
                del sys.modules[mod]
            server_mod = importlib.import_module("dcc_mcp_maya.server")
        assert hasattr(server_mod.MayaMcpServer, "find_skills")

    def test_rank_services_is_static(self):
        import importlib

        with patch.dict(sys.modules, {"dcc_mcp_core": MagicMock()}):
            for mod in [k for k in sys.modules if "dcc_mcp_maya" in k]:
                del sys.modules[mod]
            server_mod = importlib.import_module("dcc_mcp_maya.server")
        assert isinstance(
            server_mod.MayaMcpServer.__dict__["rank_services"],
            staticmethod,
        )

    def test_find_best_service_is_static(self):
        import importlib

        with patch.dict(sys.modules, {"dcc_mcp_core": MagicMock()}):
            for mod in [k for k in sys.modules if "dcc_mcp_maya" in k]:
                del sys.modules[mod]
            server_mod = importlib.import_module("dcc_mcp_maya.server")
        assert isinstance(
            server_mod.MayaMcpServer.__dict__["find_best_service"],
            staticmethod,
        )
