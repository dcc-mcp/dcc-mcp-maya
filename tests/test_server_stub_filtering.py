"""Tests for __skill__* / __group__* stub filtering (issue #174).

Verifies that ``DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST=1`` removes
``__skill__*`` stubs from the internal registry after ``register_builtin_actions``
so token-constrained MCP clients don't pay the stub-discovery overhead.

Notes
-----
- These tests directly inspect the ``MayaMcpServer`` instance rather than
  making HTTP calls so they don't depend on the MCP session handshake or
  the module-level singleton.
- In core 0.15.0+, ``__group__*`` stubs are managed by the Rust layer and
  cannot be removed via ``registry.unregister()``.  Only ``__skill__*``
  removal is asserted here.
- ``__skill__*`` stubs exposed in ``tools/list`` come from
  ``server.list_skills()`` (unloaded entries); they are removed by calling
  ``registry.unregister("__skill__<name>")`` for each.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from unittest.mock import patch

# Import third-party modules
# Import local modules
from dcc_mcp_maya._env import ENV_EXCLUDE_STUBS_FROM_TOOLS_LIST
from dcc_mcp_maya.server import MayaMcpServer

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_fresh_server(exclude_stubs: bool = False) -> MayaMcpServer:
    """Create a fresh :class:`MayaMcpServer` with ``register_builtin_actions``
    already called.  Does NOT call ``start()`` — no HTTP port needed.
    """
    env_val = "1" if exclude_stubs else "0"
    with patch.dict(os.environ, {ENV_EXCLUDE_STUBS_FROM_TOOLS_LIST: env_val}):
        server = MayaMcpServer(port=0)
        server.register_builtin_actions(minimal=True)
    return server


def _get_tools_from_registry(server: MayaMcpServer) -> list:
    """Return tool names from the Python registry (list_actions)."""
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
    """Return names of unloaded skills (``__skill__*`` stubs in tools/list)."""
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


# ── Test cases ────────────────────────────────────────────────────────────────


class TestStubFiltering:
    """Verify ``DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST`` behavior."""

    def test_default_has_skill_stubs(self):
        """Without the filter, unloaded skills appear as ``__skill__*`` stubs."""
        server = _make_fresh_server(exclude_stubs=False)
        stubs = _get_skill_stubs_from_catalog(server)
        assert stubs, (
            "Expected __skill__* stubs for unloaded skills in minimal mode; "
            "found none — check that minimal=True leaves some skills unloaded."
        )

    def test_default_has_core_tools(self):
        """Without any filter, Maya skill tools MUST be present."""
        server = _make_fresh_server(exclude_stubs=False)
        names = _get_tools_from_registry(server)
        assert names, "registry must not be empty"
        # These tools come from the always-loaded maya-scripting and maya-scene skills
        maya_tools = {"maya_scripting__execute_python", "maya_scene__get_scene_info"}
        for tool in maya_tools:
            assert tool in names, f"Maya skill tool {tool!r} must be present even without stub filtering"

    def test_exclude_stubs_removes_skill_stubs(self):
        """With the filter on, ``__skill__*`` stubs are removed from the registry."""
        server = _make_fresh_server(exclude_stubs=True)
        stubs = _get_skill_stubs_from_catalog(server)
        # After filtering, no __skill__* stubs should be registerable
        # (they were removed by _exclude_stub_tools during register_builtin_actions)
        # Verify by trying to get them via registry.get_action
        remaining = []
        for stub in stubs:
            try:
                action = server._server.registry.get_action(stub)
                if action is not None:
                    remaining.append(stub)
            except Exception:
                pass  # Not found = successfully removed
        assert not remaining, f"Expected __skill__* stubs to be removed from registry; still present: {remaining}"

    def test_exclude_stubs_keeps_core_tools(self):
        """Even with stub filtering enabled, Maya skill tools MUST remain."""
        server = _make_fresh_server(exclude_stubs=True)
        names = _get_tools_from_registry(server)
        # These tools come from the always-loaded maya-scripting and maya-scene skills
        maya_tools = {"maya_scripting__execute_python", "maya_scene__get_scene_info"}
        for tool in maya_tools:
            assert tool in names, f"Maya skill tool {tool!r} missing from registry when stubs excluded"

    def test_exclude_stubs_capability_manifest_still_works(self):
        """The capability manifest MUST still expose unloaded skills even when
        the registry filter is active."""
        server = _make_fresh_server(exclude_stubs=True)
        manifest = server.build_capability_manifest(loaded_only=False)
        capabilities = manifest.get("capabilities", [])
        unloaded = [r for r in capabilities if not r.get("loaded", True)]
        assert unloaded, (
            "Capability manifest should still expose unloaded skills when DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST=1"
        )
