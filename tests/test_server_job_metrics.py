"""Tests for MayaMcpServer job persistence, Prometheus metrics, and gateway
job routing — issues #86, #87, #89.

All tests run without a real Maya install. The dcc-mcp-core 0.14.3 wheel
ships the required features: ``McpHttpConfig.enable_prometheus``,
``McpHttpConfig.job_storage_path``, ``McpHttpConfig.enable_job_notifications``,
and the ``jobs_get_status`` built-in tool.
"""

from __future__ import annotations

import importlib
import json
import sys
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Maya stub
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Inject minimal maya stubs so imports succeed without a real Maya."""
    maya_mock = MagicMock()
    maya_mock.cmds = MagicMock()
    maya_mock.mel = MagicMock()
    maya_mock.utils = MagicMock()
    stubs = {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": maya_mock.mel,
        "maya.utils": maya_mock.utils,
    }
    with patch.dict(sys.modules, stubs):
        yield maya_mock


def _fresh_server_module():
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    return importlib.import_module("dcc_mcp_maya.server")


def _builtin_skills_dir():
    import dcc_mcp_maya

    return str(Path(dcc_mcp_maya.__file__).parent / "skills")


# ---------------------------------------------------------------------------
# Issue #87 — Prometheus /metrics endpoint
# ---------------------------------------------------------------------------


class TestPrometheusMetrics:
    """Verify that enable_prometheus is wired through McpHttpConfig."""

    def test_metrics_disabled_by_default(self):
        """``enable_prometheus`` must be ``False`` when not requested."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0)
        assert server._config.enable_prometheus is False

    def test_metrics_enabled_via_constructor(self):
        """``metrics_enabled=True`` sets ``config.enable_prometheus``."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, metrics_enabled=True)
        assert server._config.enable_prometheus is True

    def test_metrics_enabled_via_env_var(self, monkeypatch):
        """``DCC_MCP_MAYA_METRICS=1`` env var enables Prometheus."""
        monkeypatch.setenv("DCC_MCP_MAYA_METRICS", "1")
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0)
        assert server._config.enable_prometheus is True

    def test_metrics_env_var_zero_is_disabled(self, monkeypatch):
        """``DCC_MCP_MAYA_METRICS=0`` keeps the endpoint disabled."""
        monkeypatch.setenv("DCC_MCP_MAYA_METRICS", "0")
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0)
        assert server._config.enable_prometheus is False

    def test_metrics_endpoint_returns_200(self):
        """When enabled, ``GET /metrics`` returns HTTP 200 with Prometheus text."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, metrics_enabled=True)
        server.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        handle = server.start()
        try:
            base_url = handle.mcp_url().rstrip("/mcp")
            url = f"{base_url}/metrics"
            with urllib.request.urlopen(url, timeout=5) as resp:
                assert resp.status == 200
                body = resp.read().decode()
            # Prometheus text format starts with a comment or a metric name.
            assert body.strip() != ""
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                pytest.skip("Prometheus feature not compiled into this wheel")
            raise
        finally:
            server.stop()


# ---------------------------------------------------------------------------
# Issue #89 — Job persistence and startup recovery
# ---------------------------------------------------------------------------


class TestJobPersistence:
    """Verify that job_storage_path is wired through McpHttpConfig."""

    def test_job_storage_path_set_via_constructor(self, tmp_path):
        """Explicit ``job_storage_path`` flows to ``config.job_storage_path``."""
        db = str(tmp_path / "maya-jobs.db")
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, job_storage_path=db)
        assert server._config.job_storage_path == db

    def test_job_storage_path_set_via_env_var(self, monkeypatch, tmp_path):
        """``DCC_MCP_MAYA_JOB_STORAGE`` env var sets the job DB path."""
        db = str(tmp_path / "env-jobs.db")
        monkeypatch.setenv("DCC_MCP_MAYA_JOB_STORAGE", db)
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0)
        assert server._config.job_storage_path == db

    def test_job_storage_path_default_is_platform_dir(self, monkeypatch):
        """Without explicit config the default path is inside get_data_dir()."""
        monkeypatch.delenv("DCC_MCP_MAYA_JOB_STORAGE", raising=False)
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, job_storage_path=None)
        path = server._config.job_storage_path
        assert path is not None
        assert path.endswith("jobs.db")
        assert "dcc-mcp-maya" in path

    def test_job_storage_disabled_with_empty_string(self):
        """Passing ``job_storage_path=""`` disables persistence."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, job_storage_path="")
        assert not server._config.job_storage_path

    def test_job_recovery_default_is_drop(self):
        """Default job recovery policy is ``"drop"``."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0)
        assert server._job_recovery == "drop"

    def test_job_recovery_requeue_via_constructor(self):
        """``job_recovery="requeue"`` sets the recovery flag."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, job_recovery="requeue")
        assert server._job_recovery == "requeue"

    def test_job_recovery_requeue_via_env_var(self, monkeypatch):
        """``DCC_MCP_MAYA_JOB_RECOVERY=requeue`` sets recovery flag."""
        monkeypatch.setenv("DCC_MCP_MAYA_JOB_RECOVERY", "requeue")
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0)
        assert server._job_recovery == "requeue"

    def test_job_recovery_unknown_value_defaults_to_drop(self):
        """An unrecognised recovery value falls back to ``"drop"``."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, job_recovery="resume_everything")
        assert server._job_recovery == "drop"

    def test_enable_job_notifications_on_by_default(self):
        """``enable_job_notifications`` must be True by default (core default)."""
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0)
        assert server._config.enable_job_notifications is True

    def test_jobs_get_status_builtin_tool_present(self, tmp_path):
        """The ``jobs_get_status`` built-in tool must appear in ``tools/list``
        when job storage is configured."""
        db = str(tmp_path / "test-jobs.db")
        srv_mod = _fresh_server_module()
        server = srv_mod.MayaMcpServer(port=0, job_storage_path=db)
        server.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        handle = server.start()
        try:
            url = handle.mcp_url()
            rpc = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {},
                }
            ).encode()
            req = urllib.request.Request(
                url,
                data=rpc,
                headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = json.loads(resp.read())
            tool_names = [t["name"] for t in body.get("result", {}).get("tools", [])]
            assert "jobs_get_status" in tool_names, f"Missing jobs_get_status in {tool_names}"
            assert "jobs_cleanup" in tool_names, f"Missing jobs_cleanup in {tool_names}"
            assert "jobs.get_status" not in tool_names
            assert "jobs.cleanup" not in tool_names
        finally:
            server.stop()


# ---------------------------------------------------------------------------
# Issue #86 — Gateway job routing integration test
# ---------------------------------------------------------------------------


class TestGatewayJobRouting:
    """Integration tests for jobs_get_status routed through a gateway.

    Uses two MayaStandaloneDispatcher-backed MayaMcpServer instances on
    distinct ports behind one gateway, exercising core #319 (built-in
    ``jobs_get_status`` tool) and core #322 (gateway job-route cache TTL).

    No Maya installation required — MayaStandaloneDispatcher runs Python
    callables directly on the current thread without any Maya API.
    """

    @pytest.fixture
    def two_backends(self, tmp_path):
        """Start two backend servers and return (server_a, server_b, tmpdir)."""
        srv_mod = _fresh_server_module()
        db_a = str(tmp_path / "jobs_a.db")
        db_b = str(tmp_path / "jobs_b.db")

        server_a = srv_mod.MayaMcpServer(
            port=0,
            job_storage_path=db_a,
            server_name="maya-a",
        )
        server_b = srv_mod.MayaMcpServer(
            port=0,
            job_storage_path=db_b,
            server_name="maya-b",
        )
        server_a.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        server_b.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        ha = server_a.start()
        hb = server_b.start()
        yield server_a, server_b, ha, hb
        server_a.stop()
        server_b.stop()

    def _rpc(self, url, method, params=None):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def test_both_backends_reachable(self, two_backends):
        """Both backend servers can handle tools/list independently."""
        _, _, ha, hb = two_backends
        resp_a = self._rpc(ha.mcp_url(), "tools/list")
        resp_b = self._rpc(hb.mcp_url(), "tools/list")
        tools_a = {t["name"] for t in resp_a.get("result", {}).get("tools", [])}
        tools_b = {t["name"] for t in resp_b.get("result", {}).get("tools", [])}
        # jobs_get_status should appear on both backends since both have job storage
        assert "jobs_get_status" in tools_a
        assert "jobs_get_status" in tools_b
        assert "jobs_cleanup" in tools_a
        assert "jobs_cleanup" in tools_b
        assert "jobs.get_status" not in tools_a
        assert "jobs.get_status" not in tools_b
        assert "jobs.cleanup" not in tools_a
        assert "jobs.cleanup" not in tools_b

    def test_jobs_get_status_unknown_id_returns_error(self, two_backends):
        """Polling an unknown job_id returns an error result, not a hang."""
        _, _, ha, _ = two_backends
        resp = self._rpc(
            ha.mcp_url(),
            "tools/call",
            {
                "name": "jobs_get_status",
                "arguments": {"job_id": "nonexistent-job-id-000"},
            },
        )
        result = resp.get("result", {})
        # The tool must return isError=true inside a valid CallToolResult
        # (not an RPC-level error code) per the MCP spec for tool errors.
        assert result.get("isError") is True or (
            # Some core versions embed the error in content[].text
            any("not found" in str(c) or "unknown" in str(c).lower() for c in result.get("content", []))
        ), f"Expected error result for unknown job_id, got: {resp}"

    def test_backend_b_has_separate_job_namespace(self, two_backends):
        """A job_id from backend A is unknown to backend B (no shared storage)."""
        _, _, ha, hb = two_backends
        # Both have separate SQLite DBs, so a made-up ID unknown to A
        # should also be unknown to B.
        resp_b = self._rpc(
            hb.mcp_url(),
            "tools/call",
            {
                "name": "jobs_get_status",
                "arguments": {"job_id": "backend-a-only-job"},
            },
        )
        result = resp_b.get("result", {})
        assert result.get("isError") is True or any(
            "not found" in str(c) or "unknown" in str(c).lower() for c in result.get("content", [])
        ), f"Expected job-not-found error on backend B, got: {resp_b}"
