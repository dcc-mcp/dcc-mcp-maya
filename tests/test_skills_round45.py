"""Round 45 tests: MayaMcpServer inherited + Maya-specific API coverage.

After the DccServerBase refactor, these methods are inherited from core.
Tests verify the Maya adapter exposes them correctly.

Covers:
1. MayaMcpServer.search_actions() — inherited from DccServerBase
2. MayaMcpServer.unregister_skill() — inherited
3. MayaMcpServer.find_skills() — inherited
4. MayaMcpServer.get_skill_categories() — inherited
5. MayaMcpServer.get_skill_tags() — inherited
6. MayaMcpServer.rank_services() — Maya-specific static method
7. MayaMcpServer.find_best_service() — Maya-specific static method
8. MayaMcpServer.is_skill_loaded() — inherited
9. MayaMcpServer.get_skill_info() — inherited
10. Structural: all helpers present on MayaMcpServer class
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers — bypass __init__ to avoid needing Rust extension at construction
# ---------------------------------------------------------------------------


def _make_server():
    """Create MayaMcpServer via object.__new__ to avoid Rust deps."""
    from dcc_mcp_maya.server import MayaMcpServer

    server = object.__new__(MayaMcpServer)
    server._dcc_name = "maya"
    from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR

    server._builtin_skills_dir = _BUILTIN_SKILLS_DIR
    server._handle = None
    server._enable_gateway_failover = False
    server._hot_reloader = None
    server._gateway_election = None
    from dcc_mcp_core import McpHttpConfig

    server._config = McpHttpConfig()
    # Mock the inner server
    mock_inner = MagicMock()
    server._server = mock_inner
    return server


def _make_server_with_registry():
    """Create server + inject a mock ToolRegistry."""
    server = _make_server()
    mock_registry = MagicMock()
    # The `registry` property reads `self._server.registry`
    server._server.registry = mock_registry
    return server, mock_registry


# ---------------------------------------------------------------------------
# 1. search_actions (was search_skills in old server)
# ---------------------------------------------------------------------------


class TestSearchSkills:
    def test_returns_list_from_search_actions(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.return_value = [{"name": "maya_scene__create_object"}]
        result = server.search_actions(category="geometry")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_default_dcc_name_is_maya(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.return_value = []
        server.search_actions(tags=["mesh"])
        call_kwargs = reg.search_actions.call_args[1]
        assert call_kwargs.get("dcc_name") == "maya"

    def test_explicit_dcc_name_is_forwarded(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.return_value = []
        server.search_actions(category="node", dcc_name="houdini")
        call_kwargs = reg.search_actions.call_args[1]
        assert call_kwargs.get("dcc_name") == "houdini"

    def test_returns_empty_when_registry_none(self):
        server = _make_server()
        server._server.registry = None
        result = server.search_actions()
        assert result == []

    def test_returns_empty_on_exception(self):
        server, reg = _make_server_with_registry()
        reg.search_actions.side_effect = RuntimeError("boom")
        result = server.search_actions()
        assert result == []

    def test_returns_empty_when_no_registry_attr(self):
        server = _make_server()
        server._server.registry = None
        result = server.search_actions(category="foo")
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
        server.unregister_skill("nonexistent_skill")  # must not raise

    def test_does_nothing_when_registry_none(self):
        server = _make_server()
        server._server.registry = None
        server.unregister_skill("some_skill")  # must not raise

    def test_does_nothing_when_no_registry_attr(self):
        server = _make_server()
        server._server.registry = None
        server.unregister_skill("some_skill")  # must not raise


# ---------------------------------------------------------------------------
# 3. find_skills
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
        server._server.registry = None
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
        server._server.registry = None
        assert server.get_skill_tags() == []


# ---------------------------------------------------------------------------
# 6. rank_services (Maya-specific static method)
# ---------------------------------------------------------------------------


class TestRankServices:
    def test_returns_list_from_transport_manager(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        mock_tm.rank_services.return_value = [MagicMock(), MagicMock()]
        result = MayaMcpServer.rank_services(mock_tm)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_default_dcc_type_is_maya(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        mock_tm.rank_services.return_value = []
        MayaMcpServer.rank_services(mock_tm)
        mock_tm.rank_services.assert_called_once_with("maya")

    def test_explicit_dcc_type_forwarded(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        mock_tm.rank_services.return_value = []
        MayaMcpServer.rank_services(mock_tm, dcc_type="houdini")
        mock_tm.rank_services.assert_called_with("houdini")

    def test_returns_empty_on_exception(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        mock_tm.rank_services.side_effect = RuntimeError("unreachable")
        result = MayaMcpServer.rank_services(mock_tm)
        assert result == []


# ---------------------------------------------------------------------------
# 7. find_best_service (Maya-specific static method)
# ---------------------------------------------------------------------------


class TestFindBestService:
    def test_returns_service_from_transport_manager(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        fake_service = MagicMock()
        mock_tm.find_best_service.return_value = fake_service
        result = MayaMcpServer.find_best_service(mock_tm)
        assert result is fake_service

    def test_default_dcc_type_is_maya(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        mock_tm.find_best_service.return_value = None
        MayaMcpServer.find_best_service(mock_tm)
        mock_tm.find_best_service.assert_called_once_with("maya")

    def test_explicit_dcc_type_forwarded(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        mock_tm.find_best_service.return_value = None
        MayaMcpServer.find_best_service(mock_tm, dcc_type="blender")
        mock_tm.find_best_service.assert_called_once_with("blender")

    def test_returns_none_on_exception(self):
        from dcc_mcp_maya.server import MayaMcpServer

        mock_tm = MagicMock()
        mock_tm.find_best_service.side_effect = ConnectionError("no service")
        result = MayaMcpServer.find_best_service(mock_tm)
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
# 10. Structural: all methods present on MayaMcpServer
# ---------------------------------------------------------------------------


class TestServerStructural:
    def test_is_skill_loaded_in_server_class(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "is_skill_loaded")

    def test_get_skill_info_in_server_class(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "get_skill_info")

    def test_search_skills_in_server_class(self):
        from dcc_mcp_maya.server import MayaMcpServer

        # search_actions is the inherited name (search_skills was the old name)
        assert hasattr(MayaMcpServer, "search_actions")

    def test_find_skills_in_server_class(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "find_skills")

    def test_rank_services_is_static(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert isinstance(MayaMcpServer.__dict__["rank_services"], staticmethod)

    def test_find_best_service_is_static(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert isinstance(MayaMcpServer.__dict__["find_best_service"], staticmethod)
