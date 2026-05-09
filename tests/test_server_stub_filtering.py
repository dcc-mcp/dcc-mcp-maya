"""Tests for progressive skill stubs under core minimal mode."""

from __future__ import annotations

from dcc_mcp_maya.server import MayaMcpServer


def _make_fresh_server() -> MayaMcpServer:
    server = MayaMcpServer(port=0)
    server.register_builtin_actions(minimal=True)
    return server


def _get_tools_from_registry(server: MayaMcpServer) -> list:
    try:
        actions = server._server.registry.list_actions()
    except Exception:
        return []
    names = []
    for action in actions:
        if isinstance(action, dict):
            name = action.get("name", "")
        else:
            name = str(action)
        if name:
            names.append(name)
    return names


def _get_skill_stubs_from_catalog(server: MayaMcpServer) -> list:
    try:
        skills = server._server.list_skills()
    except Exception:
        return []
    stubs = []
    for skill in skills:
        if isinstance(skill, dict):
            name = skill.get("name", "")
            loaded = skill.get("loaded", False)
        else:
            name = str(skill)
            loaded = False
        if name and not loaded:
            stubs.append("__skill__" + name)
    return stubs


class TestCoreMinimalModeStubs:
    def test_minimal_mode_leaves_unloaded_skill_stubs_discoverable(self):
        server = _make_fresh_server()
        stubs = _get_skill_stubs_from_catalog(server)
        assert stubs, "Expected __skill__* stubs for unloaded skills in minimal mode"

    def test_minimal_mode_has_core_tools(self):
        server = _make_fresh_server()
        names = _get_tools_from_registry(server)
        assert names, "registry must not be empty"
        maya_tools = {"maya_scripting__execute_python", "maya_scene__get_scene_info"}
        for tool in maya_tools:
            assert tool in names, f"Maya skill tool {tool!r} must be present"

    def test_capability_manifest_exposes_unloaded_skills(self):
        server = _make_fresh_server()
        manifest = server.build_capability_manifest(loaded_only=False)
        capabilities = manifest.get("capabilities", [])
        unloaded = [r for r in capabilities if not r.get("loaded", True)]
        assert unloaded, "Capability manifest should expose unloaded skills"
