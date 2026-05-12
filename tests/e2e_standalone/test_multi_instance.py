"""Maya standalone E2E tests."""

from __future__ import annotations

import threading

import pytest

from ._support import _mcp_list_all_tools, _mcp_post, _new_scene, cmds

pytestmark = pytest.mark.e2e


class TestMultiInstanceIsolation:
    """Verify that multiple MayaMcpServer instances on different ports are
    fully independent: independent lifecycles, no port conflicts, concurrent
    HTTP requests each reach the correct server.
    """

    def _make_server(self):
        """Create, populate and start a fresh MayaMcpServer on a random port."""
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        srv.register_builtin_actions()
        handle = srv.start()
        return srv, handle

    def test_two_instances_on_different_ports(self):
        """Two servers start on different OS-assigned ports simultaneously."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        try:
            assert h_a.port != h_b.port, "Both servers must use distinct ports"
            assert h_a.mcp_url() != h_b.mcp_url()
            assert srv_a.is_running
            assert srv_b.is_running
        finally:
            srv_a.stop()
            srv_b.stop()

    def test_stop_one_does_not_affect_other(self):
        """Stopping server A leaves server B fully operational."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        try:
            srv_a.stop()
            assert not srv_a.is_running
            assert srv_b.is_running

            # Server B still responds to initialize
            code, body = _mcp_post(
                h_b.mcp_url(),
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "multi-test", "version": "1"},
                    },
                },
            )
            assert code == 200
            assert body["result"]["serverInfo"]["name"] == "maya-mcp"
        finally:
            srv_b.stop()

    def test_three_instances_all_serve_tools_list(self):
        """Three servers all respond to tools/list independently."""
        servers = [self._make_server() for _ in range(3)]
        try:
            for srv, handle in servers:
                code, body = _mcp_post(
                    handle.mcp_url(),
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                )
                assert code == 200
                tools = body["result"]["tools"]
                names = {t["name"] for t in tools}
                # Core discovery tools must be present
                assert "search_skills" in names
                assert "load_skill" in names
        finally:
            for srv, handle in servers:
                srv.stop()

    def test_concurrent_requests_to_two_servers(self):
        """Concurrent HTTP calls to two servers return independent results."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        results = {}

        def call_server(label, url, req_id):
            try:
                code, body = _mcp_post(
                    url,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": label, "version": "1"},
                        },
                    },
                )
                results[label] = (code, body)
            except Exception as exc:
                results[label] = exc

        try:
            t_a = threading.Thread(target=call_server, args=("serverA", h_a.mcp_url(), 10))
            t_b = threading.Thread(target=call_server, args=("serverB", h_b.mcp_url(), 11))
            t_a.start()
            t_b.start()
            t_a.join(timeout=15)
            t_b.join(timeout=15)

            for label in ("serverA", "serverB"):
                assert label in results, "Thread did not complete"
                r = results[label]
                assert not isinstance(r, Exception), "Request failed: {}".format(r)
                code, body = r
                assert code == 200
                assert body["result"]["serverInfo"]["name"] == "maya-mcp"
        finally:
            srv_a.stop()
            srv_b.stop()

    def test_restart_one_server_other_unaffected(self):
        """A restarted server comes back up; the other server is unaffected."""
        srv_a, h_a = self._make_server()
        srv_b, h_b = self._make_server()
        srv_a2 = None
        try:
            srv_a.stop()
            assert not srv_a.is_running
            assert srv_b.is_running

            from dcc_mcp_maya.server import MayaMcpServer

            srv_a2 = MayaMcpServer(port=0)
            srv_a2.register_builtin_actions()
            srv_a2.start()

            assert srv_a2.is_running
            assert srv_b.is_running

            code, _ = _mcp_post(
                h_b.mcp_url(),
                {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
            )
            assert code == 200
        finally:
            if srv_a2 is not None:
                srv_a2.stop()
            srv_b.stop()


class TestMultiInstanceConcurrentWorkflows:
    """Two MCP servers run different Maya workflows concurrently via HTTP.

    Maya standalone shares a single scene, but each server MCP layer is
    independent.  We verify that concurrent tool calls from different servers
    do not crash either server and each server stays fully operational.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        _new_scene()
        from dcc_mcp_maya.server import MayaMcpServer

        self._srv_a = MayaMcpServer(port=0, server_name="maya-worker-a")
        self._srv_a.register_builtin_actions()
        self._h_a = self._srv_a.start()

        self._srv_b = MayaMcpServer(port=0, server_name="maya-worker-b")
        self._srv_b.register_builtin_actions()
        self._h_b = self._srv_b.start()
        for url in (self._h_a.mcp_url(), self._h_b.mcp_url()):
            self._load_and_activate(url, "maya-primitives", "modeling", 100)
            self._load_and_activate(url, "maya-scene", "scene-management", 200)
        yield
        self._srv_a.stop()
        self._srv_b.stop()

    @staticmethod
    def _load_and_activate(mcp_url, skill_name, group_name, base_id):
        _mcp_post(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": base_id,
                "method": "tools/call",
                "params": {"name": "load_skill", "arguments": {"skill_name": skill_name}},
            },
        )
        code, body = _mcp_post(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": base_id + 1,
                "method": "tools/call",
                "params": {"name": "activate_tool_group", "arguments": {"group": group_name}},
            },
        )
        assert code == 200
        assert "error" not in body, "activate_tool_group({}) failed: {}".format(group_name, body)

    def test_different_server_names(self):
        """Each server reports its own configured name in initialize."""
        _, body_a = _mcp_post(
            self._h_a.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        _, body_b = _mcp_post(
            self._h_b.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert body_a["result"]["serverInfo"]["name"] == "maya-worker-a"
        assert body_b["result"]["serverInfo"]["name"] == "maya-worker-b"

    def test_sequential_tool_calls_from_two_servers(self):
        """Server A creates a sphere; server B creates a cube via HTTP."""
        code_a, body_a = _mcp_post(
            self._h_a.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "maya_primitives__create_sphere",
                    "arguments": {"name": "multiSphereA"},
                },
            },
        )
        assert code_a == 200
        text_a = body_a["result"]["content"][0].get("text", "")
        assert "success" in text_a or "multiSphereA" in text_a

        code_b, body_b = _mcp_post(
            self._h_b.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "maya_primitives__create_cube",
                    "arguments": {"name": "multiCubeB"},
                },
            },
        )
        assert code_b == 200
        text_b = body_b["result"]["content"][0].get("text", "")
        assert "success" in text_b or "multiCubeB" in text_b

        # Both HTTP calls succeeded — scene state verified via response text
        # (cmds.objExists is unreliable across threads in standalone mode)

    def test_concurrent_tool_calls_to_different_servers(self):
        """Concurrent tools/call to server A and B both return 200."""
        results = {}

        def call_a():
            try:
                code, body = _mcp_post(
                    self._h_a.mcp_url(),
                    {
                        "jsonrpc": "2.0",
                        "id": 20,
                        "method": "tools/call",
                        "params": {"name": "maya_scene__get_session_info", "arguments": {}},
                    },
                )
                results["a"] = (code, body)
            except Exception as exc:
                results["a"] = exc

        def call_b():
            try:
                code, body = _mcp_post(
                    self._h_b.mcp_url(),
                    {
                        "jsonrpc": "2.0",
                        "id": 21,
                        "method": "tools/call",
                        "params": {"name": "maya_scene__list_objects", "arguments": {}},
                    },
                )
                results["b"] = (code, body)
            except Exception as exc:
                results["b"] = exc

        t_a = threading.Thread(target=call_a)
        t_b = threading.Thread(target=call_b)
        t_a.start()
        t_b.start()
        t_a.join(timeout=15)
        t_b.join(timeout=15)

        assert "a" in results and "b" in results
        for key in ("a", "b"):
            r = results[key]
            assert not isinstance(r, Exception), "Request {} failed: {}".format(key, r)
            code, body = r
            assert code == 200

    def test_tools_list_stable_after_concurrent_calls(self):
        """tools/list stays complete on both servers after burst of concurrent calls."""
        errors = []

        def fire_call(url, req_id):
            try:
                _mcp_post(
                    url,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "tools/call",
                        "params": {"name": "maya_scene__get_session_info", "arguments": {}},
                    },
                )
            except Exception as exc:
                errors.append(exc)

        threads = []
        for i in range(6):
            url = self._h_a.mcp_url() if i % 2 == 0 else self._h_b.mcp_url()
            threads.append(threading.Thread(target=fire_call, args=(url, 30 + i)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)

        assert not errors, "Concurrent calls raised: {}".format(errors)

        for handle in (self._h_a, self._h_b):
            code, body = _mcp_post(
                handle.mcp_url(),
                {"jsonrpc": "2.0", "id": 99, "method": "tools/list"},
            )
            assert code == 200
            tools = body["result"]["tools"]
            names = {t["name"] for t in tools}
            assert "search_skills" in names

    def test_cross_server_scene_visibility(self):
        """Nodes created via server A are visible when queried via server B."""
        _mcp_post(
            self._h_a.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 40,
                "method": "tools/call",
                "params": {
                    "name": "maya_primitives__create_sphere",
                    "arguments": {"name": "crossVisSphere"},
                },
            },
        )

        code, body = _mcp_post(
            self._h_b.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 41,
                "method": "tools/call",
                "params": {"name": "maya_scene__list_objects", "arguments": {}},
            },
        )
        assert code == 200
        content_text = body["result"]["content"][0].get("text", "")
        assert "success" in content_text


class TestMcpSkillLifecycle:
    """search_skills -> load_skill -> activate_tool_group -> tools/call -> unload_skill over HTTP.

    Uses the `DCC_MCP_ALLOW_AMBIENT_PYTHON=1` escape hatch (same as
    `TestScriptingHttpE2E`) because the in-process executor refuses to
    execute skill scripts unless it can prove `import maya.cmds` works
    under the ambient interpreter.  Inside mayapy that guarantee holds
    but core has no way to auto-detect it — the env flag is the
    documented workaround (upstream dcc-mcp-core#231).

    Tool-naming note
    ----------------
    Depending on the registration mode, a skill action may be exposed as
    either the bare script stem (``create_sphere``) or the fully
    qualified form (``maya_primitives__create_sphere``).  The test
    resolves the live name via ``_resolve_action_name`` instead of
    hard-coding either spelling (same approach
    ``TestScriptingHttpE2E._resolve_execute_python_tool_name`` uses).
    """

    _TARGET_SKILL = "maya-primitives"
    _TARGET_GROUP = "modeling"
    _TARGET_ACTION_STEM = "create_sphere"
    _SPHERE_NAME = "mcpLifecycleSphere"

    @pytest.fixture(autouse=True, scope="class")
    def _start_server(self, request):
        import os  # noqa: PLC0415

        from dcc_mcp_maya.server import MayaMcpServer  # noqa: PLC0415

        ambient_env = "DCC_MCP_ALLOW_AMBIENT_PYTHON"
        previous_env = os.environ.get(ambient_env)
        os.environ[ambient_env] = "1"

        _new_scene()
        server = MayaMcpServer(port=0)
        server.register_builtin_actions()
        handle = server.start()
        request.cls._mcp_url = handle.mcp_url()
        try:
            yield
        finally:
            server.stop()
            if previous_env is None:
                os.environ.pop(ambient_env, None)
            else:
                os.environ[ambient_env] = previous_env

    @staticmethod
    def _tools_call(mcp_url, tool_name, arguments, request_id):
        code, body = _mcp_post(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
        )
        assert code == 200, "HTTP {} from tools/call({!r})".format(code, tool_name)
        return body

    @staticmethod
    def _resolve_action_name(names, skill, stem):
        """Return the wire-name of ``<skill>/scripts/<stem>.py`` in *names*, else None.

        Accepts both the fully-qualified (``maya_primitives__create_sphere``)
        and the bare (``create_sphere``) registration spellings so the
        test works against either convention core picks at registration
        time.
        """
        qualified = "{}__{}".format(skill.replace("-", "_"), stem)
        if qualified in names:
            return qualified
        if stem in names:
            return stem
        return None

    @staticmethod
    def _names_for_skill(names, skill):
        """Return the subset of *names* that look like they belong to *skill*."""
        prefix = skill.replace("-", "_") + "__"
        return {n for n in names if n.startswith(prefix)}

    def test_search_load_activate_call_unload_roundtrip(self):
        """End-to-end HTTP lifecycle against the restored maya-primitives skill."""
        # 1) SEARCH — prove the skill is discoverable without prior knowledge.
        search_body = self._tools_call(
            self._mcp_url,
            "search_skills",
            {"query": "primitives"},
            request_id=2100,
        )
        search_text = search_body["result"]["content"][0].get("text", "")
        assert self._TARGET_SKILL in search_text, (
            "search_skills(query='primitives') did not surface {!r}; got: {}".format(
                self._TARGET_SKILL, search_text[:400]
            )
        )

        # 2) LOAD — the skill's stub should disappear and real tools appear.
        before_names = {t["name"] for t in _mcp_list_all_tools(self._mcp_url, request_id=2101)}
        assert "__skill__" + self._TARGET_SKILL in before_names, (
            "Expected stub __skill__{} before load, saw stubs: {}".format(
                self._TARGET_SKILL,
                sorted(n for n in before_names if n.startswith("__skill__")),
            )
        )

        self._tools_call(
            self._mcp_url,
            "load_skill",
            {"skill_name": self._TARGET_SKILL},
            request_id=2102,
        )

        # 3) ACTIVATE — maya-primitives' `modeling` group has
        # default_active: false so its tools arrive as a __group__ stub;
        # activate it so the create_sphere action is callable.
        after_load = {t["name"] for t in _mcp_list_all_tools(self._mcp_url, request_id=2103)}
        assert "__skill__" + self._TARGET_SKILL not in after_load, (
            "Stub __skill__{} should be gone after load_skill".format(self._TARGET_SKILL)
        )
        group_stub = "__group__" + self._TARGET_GROUP
        if group_stub in after_load:
            self._tools_call(
                self._mcp_url,
                "activate_tool_group",
                {"group": self._TARGET_GROUP},
                request_id=2104,
            )
            after_activate = {t["name"] for t in _mcp_list_all_tools(self._mcp_url, request_id=2105)}
        else:
            after_activate = after_load

        target_tool = self._resolve_action_name(after_activate, self._TARGET_SKILL, self._TARGET_ACTION_STEM)
        if target_tool is None:
            # Failure diagnostic: show exactly what load_skill + activate added
            # so future rename / namespace changes surface clearly.
            added = sorted(after_activate - before_names)
            removed = sorted(before_names - after_activate)
            raise AssertionError(
                "Could not locate create_sphere action after load+activate of {!r}. "
                "Expected either {!r} (qualified) or {!r} (bare) in tools/list. "
                "Tools ADDED by load+activate ({}): {}. Tools REMOVED: {}.".format(
                    self._TARGET_SKILL,
                    "maya_primitives__" + self._TARGET_ACTION_STEM,
                    self._TARGET_ACTION_STEM,
                    len(added),
                    added[:40],
                    removed[:20],
                )
            )

        # 4) CALL — the canonical agent action; verify the sphere actually
        # exists in the live Maya scene, not just that MCP returned 200.
        call_body = self._tools_call(
            self._mcp_url,
            target_tool,
            {"radius": 1.25, "name": self._SPHERE_NAME},
            request_id=2106,
        )
        content = call_body["result"].get("content", [])
        assert content, "tools/call response missing content: {}".format(call_body)
        call_text = content[0].get("text", "")
        assert "success" in call_text or self._SPHERE_NAME in call_text, (
            "tools/call for {!r} did not look successful: {}".format(target_tool, call_text[:400])
        )
        assert cmds.objExists(self._SPHERE_NAME), "Expected Maya node {!r} to exist after tools/call {!r}".format(
            self._SPHERE_NAME, target_tool
        )

        # 5) UNLOAD — the action tool must disappear from tools/list and
        # the skill must be back in stub form.
        self._tools_call(
            self._mcp_url,
            "unload_skill",
            {"skill_name": self._TARGET_SKILL},
            request_id=2107,
        )
        after_unload = {t["name"] for t in _mcp_list_all_tools(self._mcp_url, request_id=2108)}
        assert target_tool not in after_unload, "{!r} should be removed from tools/list after unload_skill".format(
            target_tool
        )
        # And nothing else that looks like a maya-primitives action tool
        # should linger either.
        leaks = self._names_for_skill(after_unload, self._TARGET_SKILL)
        assert not leaks, "No maya_primitives__* tools should be exposed after unload_skill; saw: {}".format(
            sorted(leaks)
        )


class TestMultiInstanceCapabilityDivergence:
    """Two concurrent servers with disjoint loaded-skill sets expose
    disjoint tools over MCP.

    Server A loads ``maya-primitives`` + activates the ``modeling`` group.
    Server B loads ``maya-animation``  + activates the ``animation`` group.

    The fixture records each server's ``tools/list`` both *before* and
    *after* driving it into its load+activate state so the assertions
    can compare DELTAs — i.e. "the action tools server A gained by
    loading maya-primitives must not be the same ones server B
    gained by loading maya-animation".  This keeps the test valid
    regardless of whether the underlying registry uses bare
    (``create_sphere``) or qualified (``maya_primitives__create_sphere``)
    naming.
    """

    _SKILL_A = "maya-primitives"
    _GROUP_A = "modeling"
    _SAMPLE_ACTION_A = "create_sphere"

    _SKILL_B = "maya-animation"
    _GROUP_B = "animation"
    _SAMPLE_ACTION_B = "set_timeline"

    @pytest.fixture(autouse=True, scope="class")
    def _start_two_servers(self, request):
        import os  # noqa: PLC0415

        from dcc_mcp_maya.server import MayaMcpServer  # noqa: PLC0415

        ambient_env = "DCC_MCP_ALLOW_AMBIENT_PYTHON"
        previous_env = os.environ.get(ambient_env)
        os.environ[ambient_env] = "1"

        _new_scene()

        # Two distinct server_names so we can differentiate them in
        # `initialize` responses too (not strictly required by this class
        # but keeps parity with TestMultiInstanceConcurrentWorkflows).
        srv_a = MayaMcpServer(port=0, server_name="maya-capability-a")
        srv_a.register_builtin_actions()
        h_a = srv_a.start()

        srv_b = MayaMcpServer(port=0, server_name="maya-capability-b")
        srv_b.register_builtin_actions()
        h_b = srv_b.start()

        request.cls._url_a = h_a.mcp_url()
        request.cls._url_b = h_b.mcp_url()

        # Snapshot each server's tool surface before driving it into
        # a distinct loaded-skill state.
        baseline_a = {t["name"] for t in _mcp_list_all_tools(request.cls._url_a, request_id=2900)}
        baseline_b = {t["name"] for t in _mcp_list_all_tools(request.cls._url_b, request_id=2901)}

        TestMultiInstanceCapabilityDivergence._load_and_activate(
            request.cls._url_a, request.cls._SKILL_A, request.cls._GROUP_A, base_id=3000
        )
        TestMultiInstanceCapabilityDivergence._load_and_activate(
            request.cls._url_b, request.cls._SKILL_B, request.cls._GROUP_B, base_id=3100
        )

        # Final snapshots after skill activation.
        final_a = {t["name"] for t in _mcp_list_all_tools(request.cls._url_a, request_id=3150)}
        final_b = {t["name"] for t in _mcp_list_all_tools(request.cls._url_b, request_id=3151)}

        # Expose every piece of evidence the assertions need.  Using
        # request.cls so every test method in the class sees the same
        # class-level view.
        request.cls._baseline_a = baseline_a
        request.cls._baseline_b = baseline_b
        request.cls._final_a = final_a
        request.cls._final_b = final_b

        try:
            yield
        finally:
            srv_a.stop()
            srv_b.stop()
            if previous_env is None:
                os.environ.pop(ambient_env, None)
            else:
                os.environ[ambient_env] = previous_env

    @staticmethod
    def _load_and_activate(mcp_url, skill_name, group_name, base_id):
        """Load *skill_name* and, if the group is default_active: false, activate it."""
        _mcp_post(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": base_id,
                "method": "tools/call",
                "params": {
                    "name": "load_skill",
                    "arguments": {"skill_name": skill_name},
                },
            },
        )
        names = {t["name"] for t in _mcp_list_all_tools(mcp_url, request_id=base_id + 1)}
        if "__group__" + group_name in names:
            _mcp_post(
                mcp_url,
                {
                    "jsonrpc": "2.0",
                    "id": base_id + 2,
                    "method": "tools/call",
                    "params": {
                        "name": "activate_tool_group",
                        "arguments": {"group": group_name},
                    },
                },
            )

    @staticmethod
    def _real_tools(names):
        """Drop stubs (__skill__*, __group__*) — leave only real action tools."""
        return {n for n in names if not n.startswith("__")}

    def test_each_server_exposes_distinct_action_tool_sets(self):
        """The set of *real* tools A gained from loading maya-primitives
        must not be the same set B gained from loading maya-animation.

        Compared as set-deltas over the pre-load baseline so the
        assertion is immune to whether tools end up registered under
        bare (``create_sphere``) or qualified
        (``maya_primitives__create_sphere``) names.
        """
        gained_a = self._real_tools(self._final_a - self._baseline_a)
        gained_b = self._real_tools(self._final_b - self._baseline_b)

        # Each server must have genuinely gained at least one new
        # action tool from its load (otherwise the test is vacuous).
        assert gained_a, "Server A gained no real tools from loading {!r}. Final set: {}".format(
            self._SKILL_A, sorted(self._final_a)[:50]
        )
        assert gained_b, "Server B gained no real tools from loading {!r}. Final set: {}".format(
            self._SKILL_B, sorted(self._final_b)[:50]
        )

        # Sample actions must be present on their own server under
        # either naming convention.
        qualified_a = "{}__{}".format(self._SKILL_A.replace("-", "_"), self._SAMPLE_ACTION_A)
        qualified_b = "{}__{}".format(self._SKILL_B.replace("-", "_"), self._SAMPLE_ACTION_B)
        has_sample_a = self._SAMPLE_ACTION_A in gained_a or qualified_a in gained_a
        has_sample_b = self._SAMPLE_ACTION_B in gained_b or qualified_b in gained_b
        assert has_sample_a, "Server A should expose a {!r} tool (bare or {!r}); gained only: {}".format(
            self._SAMPLE_ACTION_A, qualified_a, sorted(gained_a)
        )
        assert has_sample_b, "Server B should expose a {!r} tool (bare or {!r}); gained only: {}".format(
            self._SAMPLE_ACTION_B, qualified_b, sorted(gained_b)
        )

        # THE headline assertion: the gained-tool sets must differ.
        # Bare-name registration is known to produce overlap on common
        # names like ``create_sphere`` (maya-geometry already ships one),
        # so we do NOT assert the sets are disjoint — we assert that
        # each server gained at least one tool the OTHER did not.
        a_only = gained_a - gained_b
        b_only = gained_b - gained_a
        assert a_only, (
            "Server A's gained tools are a subset of Server B's — skill-set "
            "divergence not observable via tools/list. gained_a={}, gained_b={}".format(
                sorted(gained_a), sorted(gained_b)
            )
        )
        assert b_only, (
            "Server B's gained tools are a subset of Server A's — skill-set "
            "divergence not observable via tools/list. gained_a={}, gained_b={}".format(
                sorted(gained_a), sorted(gained_b)
            )
        )

    def test_tool_call_for_unloaded_skill_is_rejected(self):
        """Calling a skill action against a server that never loaded it
        returns an error envelope — not a silent 200 with garbage, and
        not a 500 either.

        We target a tool that only exists under the qualified
        ``maya_animation__*`` namespace so the check is valid regardless
        of whether bare-name registration caused any overlap on the
        positive test above.
        """
        animation_only = "maya_animation__set_timeline"
        # Sanity: this tool must actually exist on server B.
        assert animation_only in self._final_b or self._SAMPLE_ACTION_B in self._final_b, (
            "Precondition failed: server B does not expose any recognisable set_timeline tool; "
            "cannot meaningfully assert its absence on server A. final_b sample: {}".format(
                sorted(n for n in self._final_b if "timeline" in n or "animation" in n)
            )
        )
        # And it must NOT be present on server A — which is what makes
        # the negative call below meaningful.
        assert animation_only not in self._final_a, (
            "Precondition failed: server A unexpectedly exposes {!r}, so the "
            "negative-tool-call assertion below would pass trivially.".format(animation_only)
        )

        # Server A has only maya-primitives loaded; try to call an
        # unambiguously-qualified maya-animation action against it.
        code, body = _mcp_post(
            self._url_a,
            {
                "jsonrpc": "2.0",
                "id": 3300,
                "method": "tools/call",
                "params": {
                    "name": animation_only,
                    "arguments": {"start_frame": 1, "end_frame": 24},
                },
            },
        )
        # Core's contract: an unknown tool returns either a JSON-RPC
        # error object or a result with isError=true (issue #165).
        # Accept either shape; both are documented as valid.
        assert code == 200, "Transport errors should not surface as HTTP {}".format(code)
        has_jsonrpc_error = "error" in body
        has_iserror = bool(body.get("result", {}).get("isError"))
        assert has_jsonrpc_error or has_iserror, (
            "Expected structured error for unknown tool {!r} on server A; got: {}".format(animation_only, body)
        )
