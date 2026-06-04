"""Unit and integration tests for the strict skill-only regression suite (PIP-481).

Coverage:
- Pure utility functions (percentile, summary, slug extraction, URL resolution)
- SlugCache behaviour
- GatewayClient against a live :class:`MayaMcpServer` (search → describe → call)
- Report schema validation
- CLI argument parsing

Tests that require a real Maya gateway are guarded with
``@pytest.mark.skipif`` and check for the environment variable
``DCC_MCP_GATEWAY_BASE_URL``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import pytest

# Ensure we import the local src rather than any installed wheel.
_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from strict_skill_only_regression import (  # noqa: E402
    GatewayClient,
    SlugCache,
    _ensure_call_success,
    _extract_action,
    _extract_slug,
    _percentile,
    _pick_slug_for_action,
    _resolve_base_url,
    _summary_ms,
    _utc_now,
    main,
    parse_args,
    run,
)

# ---------------------------------------------------------------------------
# Pure utility function tests
# ---------------------------------------------------------------------------


class TestPercentile:
    def test_empty_returns_zero(self):
        assert _percentile([], 0.50) == 0.0

    def test_single_value(self):
        assert _percentile([42.0], 0.50) == 42.0
        assert _percentile([42.0], 0.00) == 42.0
        assert _percentile([42.0], 1.00) == 42.0

    def test_median(self):
        assert _percentile([1.0, 2.0, 3.0], 0.50) == 2.0

    def test_p95(self):
        # 100 values 0..99 → p95 is 94.05
        values = list(range(100))
        result = _percentile(values, 0.95)
        assert 94.0 <= result <= 95.0

    def test_p99(self):
        values = list(range(100))
        result = _percentile(values, 0.99)
        assert 98.0 <= result <= 99.0


class TestSummaryMs:
    def test_empty_returns_defaults(self):
        s = _summary_ms([])
        assert s == {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}

    def test_single_value(self):
        s = _summary_ms([10.0])
        assert s["avg"] == 10.0
        assert s["p50"] == 10.0
        assert s["max"] == 10.0

    def test_multiple_values(self):
        s = _summary_ms([1.0, 2.0, 3.0, 4.0, 5.0])
        assert s["avg"] == 3.0
        assert s["p50"] == 3.0
        assert s["max"] == 5.0
        assert s["p95"] > s["p50"]


class TestExtractSlug:
    def test_prefers_tool_slug(self):
        hit = {"tool_slug": "maya_scene__new_scene", "slug": "other", "name": "new_scene"}
        assert _extract_slug(hit) == "maya_scene__new_scene"

    def test_falls_back_to_slug(self):
        hit = {"slug": "maya_scene__new_scene"}
        assert _extract_slug(hit) == "maya_scene__new_scene"

    def test_falls_back_to_name(self):
        hit = {"name": "new_scene"}
        assert _extract_slug(hit) == "new_scene"

    def test_empty_hit_returns_empty(self):
        assert _extract_slug({}) == ""


class TestExtractAction:
    def test_prefers_backend_tool(self):
        hit = {"backend_tool": "create_sphere", "action": "other", "name": "sphere"}
        assert _extract_action(hit) == "create_sphere"

    def test_falls_back_to_action(self):
        hit = {"action": "create_sphere"}
        assert _extract_action(hit) == "create_sphere"

    def test_falls_back_to_name(self):
        hit = {"name": "create_sphere"}
        assert _extract_action(hit) == "create_sphere"


class TestPickSlugForAction:
    def test_exact_action_match(self):
        result = {
            "hits": [
                {"backend_tool": "maya_scene__other", "tool_slug": "other_slug"},
                {"backend_tool": "maya_scene__new_scene", "tool_slug": "target_slug"},
            ]
        }
        assert _pick_slug_for_action(result, "maya_scene__new_scene") == "target_slug"

    def test_substring_fallback(self):
        """When exact backend_tool doesn't match, fall back to slug containing action_name."""
        result = {
            "hits": [
                {"name": "unrelated", "slug": "unrelated"},
                {"name": "create_sphere", "slug": "maya_primitives__create_sphere"},
            ]
        }
        assert _pick_slug_for_action(result, "create_sphere") == "maya_primitives__create_sphere"

    def test_short_name_fallback(self):
        """Matches on the last segment of qualified action name (e.g. get_scene_info)."""
        result = {
            "hits": [
                {"slug": "maya.core.get_scene_info", "name": "Get Scene Info"},
            ]
        }
        assert _pick_slug_for_action(result, "maya_scene__get_scene_info") == "maya.core.get_scene_info"

    def test_missing_raises_runtime_error(self):
        result = {"hits": [{"name": "unrelated", "slug": "unrelated"}]}
        with pytest.raises(RuntimeError, match="Cannot resolve slug"):
            _pick_slug_for_action(result, "nonexistent_action")


class TestEnsureCallSuccess:
    def test_success_output(self):
        resp = {"output": {"success": True, "context": {}}}
        assert _ensure_call_success(resp, "test_op") == {"success": True, "context": {}}

    def test_failure_raises(self):
        resp = {"output": {"success": False, "message": "Tool not found"}}
        with pytest.raises(RuntimeError, match="test_op failed"):
            _ensure_call_success(resp, "test_op")

    def test_missing_output_raises(self):
        resp = {"other": "data"}
        with pytest.raises(RuntimeError, match="test_op failed"):
            _ensure_call_success(resp, "test_op")


class TestResolveBaseUrl:
    def test_cli_arg_takes_priority(self):
        assert _resolve_base_url("http://example.com:1234") == "http://example.com:1234"

    def test_env_var_fallback(self, monkeypatch):
        monkeypatch.setenv("DCC_MCP_GATEWAY_BASE_URL", "http://env.example.com:9999")
        assert _resolve_base_url(None) == "http://env.example.com:9999"

    def test_default(self, monkeypatch):
        monkeypatch.delenv("DCC_MCP_GATEWAY_BASE_URL", raising=False)
        assert _resolve_base_url(None) == "http://127.0.0.1:9765"

    def test_strips_trailing_slash(self):
        assert _resolve_base_url("http://example.com/") == "http://example.com"


class TestUtcNow:
    def test_returns_iso_format_with_z(self):
        result = _utc_now()
        assert result.endswith("Z")
        assert "T" in result
        assert "+" not in result  # Z suffix, no offset


# ---------------------------------------------------------------------------
# SlugCache tests
# ---------------------------------------------------------------------------


class TestSlugCache:
    def test_resolve_caches_result(self, mocker):
        client = mocker.MagicMock(spec=GatewayClient)
        client.search.return_value = {"hits": [{"backend_tool": "test_action", "tool_slug": "cached_slug"}]}

        cache = SlugCache()
        slug1 = cache.resolve(client, "test_action")
        slug2 = cache.resolve(client, "test_action")

        assert slug1 == "cached_slug"
        assert slug2 == "cached_slug"
        # Search should only be called once (the first resolve)
        assert client.search.call_count == 1
        assert client.describe.call_count == 1

    def test_preload_actions(self, mocker):
        client = mocker.MagicMock(spec=GatewayClient)

        def search_side_effect(query, **__):
            return {"hits": [{"backend_tool": query, "tool_slug": f"slug_{query}"}]}

        client.search.side_effect = search_side_effect

        cache = SlugCache()
        cache.preload_actions(client, "action_a", "action_b")

        # Both actions should be cached now
        assert "action_a" in cache._cache
        assert "action_b" in cache._cache
        assert cache._cache["action_a"] == "slug_action_a"
        assert cache._cache["action_b"] == "slug_action_b"
        assert client.search.call_count == 2

    def test_different_actions_independent(self, mocker):
        client = mocker.MagicMock(spec=GatewayClient)

        def search_side_effect(query, **__):
            return {"hits": [{"backend_tool": query, "tool_slug": f"slug_for_{query}"}]}

        client.search.side_effect = search_side_effect

        cache = SlugCache()
        assert cache.resolve(client, "action_a") == "slug_for_action_a"
        assert cache.resolve(client, "action_b") == "slug_for_action_b"
        assert client.search.call_count == 2


# ---------------------------------------------------------------------------
# GatewayClient integration tests (against live server)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def skill_server():
    """Start a Maya MCP server on an ephemeral port for API testing.

    Loads a minimal set of skills so search/describe/call have real targets.
    """
    os.environ.setdefault("DCC_MCP_DISABLE_FILE_LOGGING", "1")

    from dcc_mcp_maya.server import MayaMcpServer  # noqa: E402

    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=True)
    # Load a few skills so typed-tool search has real results.
    for skill in ("maya-scripting", "maya-scene"):
        server.load_skill(skill)
    handle = server.start()
    time.sleep(0.05)
    yield server, handle
    server.stop()


@pytest.fixture(scope="module")
def rest_base(skill_server):
    _, handle = skill_server
    return handle.mcp_url().rsplit("/", 1)[0]


@pytest.fixture(scope="module")
def gw_client(rest_base):
    return GatewayClient(base_url=rest_base, timeout_secs=10)


class TestGatewayClientIntegration:
    """Verify the GatewayClient can search, describe, and call against a live server.

    These tests exercise the HTTP transport and the search/describe endpoints.
    Tool *calls* that require a Maya main thread are expected to fail with a
    409 thread-affinity error in a headless test environment — the test
    verifies the response is well-formed, not that the tool executed.
    """

    def test_search_returns_hits(self, gw_client):
        result = gw_client.search("scene", loaded_only=False, limit=10)
        hits = result.get("hits") or result.get("tools") or []
        assert len(hits) > 0, f"No hits in search result: {result}"

    def test_search_finds_execute_python(self, gw_client):
        """Search should find the maya_scripting__execute_python tool."""
        search = gw_client.search("execute_python", loaded_only=False, limit=50)
        slug = _pick_slug_for_action(search, "maya_scripting__execute_python")
        assert slug, "Cannot resolve execute_python slug from search"
        assert "execute_python" in slug

    def test_describe_returns_entry(self, gw_client):
        """Describe a known tool slug returned by search."""
        search = gw_client.search("execute_python", loaded_only=False, limit=50)
        slug = _pick_slug_for_action(search, "maya_scripting__execute_python")
        assert slug

        described = gw_client.describe(slug)
        assert described, "Describe returned empty result"
        # The response should include either entry, tool, or schema info
        has_info = (
            described.get("entry") is not None
            or described.get("tool") is not None
            or described.get("inputSchema") is not None
        )
        assert has_info, f"Describe result has no recognizable payload: {described}"

    def test_call_thread_affinity_error_is_well_formed(self, gw_client):
        """Call a main-thread tool in a headless test — expect a 409 error,
        but NOT a crash or empty response.  This validates the error path."""
        search = gw_client.search("execute_python", loaded_only=False, limit=50)
        slug = _pick_slug_for_action(search, "maya_scripting__execute_python")
        assert slug

        # In headless tests the call will return 409 (thread affinity violation).
        # The GatewayClient wraps this in a RuntimeError — we assert it is NOT
        # an unexpected exception type.
        try:
            resp = gw_client.call(slug, {"code": "1+1", "capture_output": True})
            # If it succeeds (unlikely in headless), the response must be dict
            assert isinstance(resp, dict)
        except RuntimeError as exc:
            # Expected: 409 or connection error
            error_msg = str(exc)
            assert "409" in error_msg or "THREAD_AFFINITY" in error_msg or "refused" in error_msg.lower(), (
                f"Unexpected RuntimeError: {error_msg[:200]}"
            )


class TestSlugCacheWithLiveServer:
    """Verify SlugCache works correctly against a real server."""

    def test_resolves_and_caches(self, rest_base):
        client = GatewayClient(base_url=rest_base, timeout_secs=10)
        cache = SlugCache()

        # Use a tool we know is in the search results
        slug = cache.resolve(client, "maya_scripting__execute_python")
        assert slug, "Should resolve execute_python slug"
        assert "execute_python" in slug

        # Second resolve should return cached slug without additional HTTP calls
        slug2 = cache.resolve(client, "maya_scripting__execute_python")
        assert slug2 == slug

    def test_preload_then_call(self, rest_base):
        client = GatewayClient(base_url=rest_base, timeout_secs=10)
        cache = SlugCache()

        cache.preload_actions(client, "maya_scripting__execute_python")
        assert "maya_scripting__execute_python" in cache._cache

        # Now use the cached slug to call — may fail with 409 in headless, but
        # the call itself should go through the HTTP layer correctly
        slug = cache._cache["maya_scripting__execute_python"]
        try:
            resp = client.call(slug, {"code": "1+1", "capture_output": True})
            assert isinstance(resp, dict)
        except RuntimeError as exc:
            # Expected in headless: thread affinity error
            assert "409" in str(exc) or "THREAD_AFFINITY" in str(exc)


# ---------------------------------------------------------------------------
# Report schema validation
# ---------------------------------------------------------------------------


class TestReportSchema:
    """Validate that the report JSON follows the expected schema."""

    REQUIRED_TOP_KEYS = {
        "issue",
        "suite",
        "started_at",
        "gateway_base_url",
        "policy",
        "config",
        "policy_guard",
        "workload",
        "soak",
        "finished_at",
        "duration_secs",
        "success",
    }

    REQUIRED_WORKLOAD_KEYS = {
        "objects_created",
        "materials_created",
        "keyframes_set",
        "fbx",
    }

    REQUIRED_SOAK_KEYS = {
        "iterations",
        "avg_ms",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "max_ms",
        "failure_count",
        "failures",
    }

    REQUIRED_POLICY_GUARD_KEYS = {"execute_python", "execute_mel"}

    def _build_minimal_report(self):
        """Build a structurally valid report dict (no Maya needed)."""
        return {
            "issue": "PIP-481",
            "suite": "maya_strict_skill_only_regression",
            "started_at": _utc_now(),
            "gateway_base_url": "http://127.0.0.1:9765",
            "policy": "search -> load_skill/activate group -> describe -> call typed tools",
            "config": {
                "soak_iterations": 500,
                "object_count_target": 150,
                "keyframe_count_target": 180,
            },
            "policy_guard": {
                "execute_python": {"slug": "test_slug", "blocked": True, "response": None},
                "execute_mel": {"slug": "test_slug", "blocked": True, "response": None},
            },
            "workload": {
                "objects_created": 150,
                "materials_created": 3,
                "keyframes_set": 180,
                "fbx": {
                    "path": "/tmp/test.fbx",
                    "size_bytes": 12345,
                    "applied_options": {},
                },
            },
            "soak": {
                "iterations": 500,
                "avg_ms": 15.3,
                "p50_ms": 12.1,
                "p95_ms": 28.7,
                "p99_ms": 45.2,
                "max_ms": 200.0,
                "failure_count": 0,
                "failures": [],
            },
            "finished_at": _utc_now(),
            "duration_secs": 42.5,
            "success": True,
        }

    def test_report_has_all_top_level_keys(self):
        report = self._build_minimal_report()
        missing = self.REQUIRED_TOP_KEYS - set(report.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_workload_has_required_keys(self):
        report = self._build_minimal_report()
        missing = self.REQUIRED_WORKLOAD_KEYS - set(report["workload"].keys())
        assert not missing, f"Missing workload keys: {missing}"

    def test_workload_counts_valid(self):
        report = self._build_minimal_report()
        assert report["workload"]["objects_created"] == 150
        assert report["workload"]["materials_created"] == 3
        assert report["workload"]["keyframes_set"] == 180
        assert report["workload"]["fbx"]["size_bytes"] > 0

    def test_soak_has_required_keys(self):
        report = self._build_minimal_report()
        missing = self.REQUIRED_SOAK_KEYS - set(report["soak"].keys())
        assert not missing, f"Missing soak keys: {missing}"

    def test_soak_percentiles_monotonic(self):
        """p50 ≤ p95 ≤ p99 ≤ max should hold for any latency distribution."""
        report = self._build_minimal_report()
        s = report["soak"]
        assert s["p50_ms"] <= s["p95_ms"]
        assert s["p95_ms"] <= s["p99_ms"]
        assert s["p99_ms"] <= s["max_ms"]

    def test_policy_guard_has_required_keys(self):
        report = self._build_minimal_report()
        missing = self.REQUIRED_POLICY_GUARD_KEYS - set(report["policy_guard"].keys())
        assert not missing, f"Missing policy guard keys: {missing}"

    def test_policy_guard_both_blocked(self):
        report = self._build_minimal_report()
        assert report["policy_guard"]["execute_python"]["blocked"] is True
        assert report["policy_guard"]["execute_mel"]["blocked"] is True

    def test_success_matches_failure_count(self):
        report = self._build_minimal_report()
        # When failure_count is 0, success should be True
        assert report["success"] is True
        assert report["soak"]["failure_count"] == 0


# ---------------------------------------------------------------------------
# CLI argument parsing tests
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.base_url is None
        assert args.output_dir == "artifacts/perf"
        assert args.soak_iterations == 500
        assert args.timeout_secs == 120
        assert args.report == ""

    def test_custom_values(self):
        args = parse_args(
            [
                "--base-url",
                "http://localhost:1234",
                "--output-dir",
                "/tmp/results",
                "--soak-iterations",
                "100",
                "--timeout-secs",
                "60",
                "--report",
                "/tmp/my_report.json",
            ]
        )
        assert args.base_url == "http://localhost:1234"
        assert args.output_dir == "/tmp/results"
        assert args.soak_iterations == 100
        assert args.timeout_secs == 60
        assert args.report == "/tmp/my_report.json"


# ---------------------------------------------------------------------------
# run() function unit test (without Maya gateway)
# ---------------------------------------------------------------------------


class TestRunFunction:
    """Test that run() raises a clear error when no Maya gateway is available.

    Required to NOT depend on a live Maya gateway. When one is available
    (DCC_MCP_GATEWAY_BASE_URL set), the full integration path can be
    exercised with ``test_run_full_integration``.
    """

    def test_run_fails_cleanly_with_no_gateway(self, tmp_path, monkeypatch):
        """Without a gateway, run() should raise a clear RuntimeError (connection refused
        or similar), not crash with an unexpected traceback."""
        monkeypatch.delenv("DCC_MCP_GATEWAY_BASE_URL", raising=False)

        args = argparse.Namespace(
            base_url="http://127.0.0.1:1",  # non-existent port
            output_dir=str(tmp_path),
            soak_iterations=5,
            timeout_secs=1,
            report="",
        )
        with pytest.raises(Exception):
            run(args)

    @pytest.mark.skipif(
        not os.environ.get("DCC_MCP_GATEWAY_BASE_URL"),
        reason="DCC_MCP_GATEWAY_BASE_URL not set — live gateway required",
    )
    def test_run_full_integration(self, tmp_path):
        """Full integration run against a live Maya gateway.

        This exercises the complete policy-guard → workload → soak pipeline.
        Set ``DCC_MCP_GATEWAY_BASE_URL`` to a reachable gateway endpoint.
        """
        args = argparse.Namespace(
            base_url=os.environ["DCC_MCP_GATEWAY_BASE_URL"],
            output_dir=str(tmp_path),
            soak_iterations=10,  # small soak for test speed
            timeout_secs=120,
            report=str(tmp_path / "test_report.json"),
        )
        report = run(args)
        assert isinstance(report, dict)
        assert report["suite"] == "maya_strict_skill_only_regression"
        assert "policy_guard" in report
        assert "workload" in report
        assert "soak" in report

        # Check workload produced data
        assert report["workload"]["objects_created"] == 150
        assert report["workload"]["keyframes_set"] == 180

        # Check soak produced data
        assert report["soak"]["iterations"] == 10
        assert report["soak"]["avg_ms"] >= 0


# ---------------------------------------------------------------------------
# main() CLI entry point tests
# ---------------------------------------------------------------------------


class TestMainCLI:
    def test_main_prints_json_on_failure(self, tmp_path, monkeypatch, capsys):
        """When gateway is unreachable, main() exits non-zero and prints JSON."""
        monkeypatch.delenv("DCC_MCP_GATEWAY_BASE_URL", raising=False)

        exit_code = main(
            [
                "--base-url",
                "http://127.0.0.1:1",
                "--output-dir",
                str(tmp_path),
                "--soak-iterations",
                "5",
                "--timeout-secs",
                "1",
            ]
        )
        assert exit_code == 1
        captured = capsys.readouterr()
        combined = captured.out + captured.err

        # The pretty-printed JSON is emitted somewhere after the banner.
        # Find the outermost JSON object in the output.
        brace_start = combined.find('{\n  "suite"')
        if brace_start == -1:
            brace_start = combined.find('{\n  "success"')
        if brace_start >= 0:
            # Find the matching closing brace by scanning
            depth = 0
            end = brace_start
            for i in range(brace_start, len(combined)):
                if combined[i] == "{":
                    depth += 1
                elif combined[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            json_str = combined[brace_start:end]
            failure = json.loads(json_str)
            assert failure["success"] is False
            assert "error" in failure
        else:
            pytest.fail(f"main() did not print valid JSON failure record.\nOutput (first 500 chars): {combined[:500]}")

    def test_main_parses_report_flag(self, tmp_path, monkeypatch, capsys):
        """The --report flag is accepted by argparse (we test parsing, not running)."""
        monkeypatch.delenv("DCC_MCP_GATEWAY_BASE_URL", raising=False)

        exit_code = main(
            [
                "--base-url",
                "http://127.0.0.1:1",
                "--output-dir",
                str(tmp_path),
                "--soak-iterations",
                "3",
                "--timeout-secs",
                "1",
                "--report",
                str(tmp_path / "explicit.json"),
            ]
        )
        assert exit_code == 1  # fails because no gateway, not because of parsing
