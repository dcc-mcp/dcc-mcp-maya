"""HTTP transport coverage for Maya MCP — in-process server and sidecar.

* **In-process** — :class:`~dcc_mcp_maya.server.MayaMcpServer` exposes the full
  Streamable HTTP MCP surface (``POST /mcp``) and the REST skill API
  (``GET/POST /v1/*``). Deeper scenarios live in
  :mod:`tests.test_http_dynamic_skill_api` and :mod:`tests.test_rest_skill_api`.

* **Sidecar** — ``dcc-mcp-server sidecar`` publishes a minimal MCP listener
  (``initialize``, ``ping``, ``tools/call`` only) that forwards to the in-Maya
  Qt JSON-line dispatcher. These tests spin a stub ``qtserver://`` peer that
  calls :func:`dcc_mcp_maya.sidecar.dispatch_payload` against a real
  :class:`MayaMcpServer` fixture.
"""

from __future__ import annotations

import json
import textwrap
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from dcc_mcp_maya.server import MayaMcpServer
from dcc_mcp_maya.sidecar import start_sidecar, stop_sidecar
from tests._transport_support import (
    ParentSurrogate,
    QtJsonLineStubServer,
    allocate_ephemeral_port,
    mcp_initialize,
    mcp_post,
    mcp_url_from_registry_entry,
    qt_stub_factory,
    rest_get_json,
    rest_post_json,
    sidecar_binary_available,
    wait_for_sidecar_registry_row,
)


def _qualified_action_name(skill: str, stem: str) -> str:
    return "{}__{}".format(skill.replace("-", "_"), stem)


def _write_echo_skill(root: Path, name: str) -> Path:
    pkg = root / name
    (pkg / "scripts").mkdir(parents=True)
    (pkg / "SKILL.md").write_text(
        textwrap.dedent(
            """\
            ---
            name: {name}
            description: Transport test skill.
            license: MIT
            metadata:
              dcc-mcp:
                dcc: maya
                layer: domain
                version: 1.0.0
                tools: tools.yaml
            ---

            # {name}
            """
        ).format(name=name),
        encoding="utf-8",
    )
    (pkg / "tools.yaml").write_text(
        textwrap.dedent(
            """\
            tools:
              - name: echo
                description: Echo kwargs for transport tests.
                execution: sync
                affinity: any
                group: core
                inputSchema:
                  type: object
                  additionalProperties: true
            """
        ),
        encoding="utf-8",
    )
    (pkg / "groups.yaml").write_text(
        "groups:\n- name: core\n  description: core\n  default_active: true\n  tools:\n  - echo\n",
        encoding="utf-8",
    )
    (pkg / "scripts" / "echo.py").write_text(
        textwrap.dedent(
            """\
            def main(**kwargs):
                return {"success": True, "message": "echo", "context": {"args": kwargs}}
            """
        ),
        encoding="utf-8",
    )
    return pkg


def _extract_tool_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict) and "success" in result:
        return result
    content = result.get("content") or []
    if content and isinstance(content[0], dict):
        text = content[0].get("text") or ""
        if text:
            return json.loads(text)
    return result


@pytest.fixture(scope="module")
def echo_maya_server(tmp_path_factory):
    """Running in-process server with a single ``affinity: any`` echo tool."""
    tmp_path = tmp_path_factory.mktemp("maya-http-transport")
    skill_pkg = _write_echo_skill(tmp_path, "transport-echo")
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(
        extra_skill_paths=[str(skill_pkg.parent)],
        include_bundled=False,
        minimal=False,
    )
    assert server.load_skill("transport-echo")
    handle = server.start()
    time.sleep(0.05)
    action = _qualified_action_name("transport-echo", "echo")
    try:
        yield server, handle, action
    finally:
        server.stop()


class TestInProcessHttpApi:
    """Full MCP + REST on the embedded :class:`MayaMcpServer` HTTP listener."""

    def test_mcp_initialize_and_tools_list(self, echo_maya_server):
        _, handle, _ = echo_maya_server
        mcp_url = handle.mcp_url()
        session = mcp_initialize(mcp_url, client_name="maya-inprocess-http")

        listing = mcp_post(
            mcp_url,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            session_id=session,
        )
        names = {t["name"] for t in listing["result"]["tools"]}
        assert "load_skill" in names

    def test_mcp_tools_call_round_trip(self, echo_maya_server):
        _, handle, action = echo_maya_server
        mcp_url = handle.mcp_url()
        session = mcp_initialize(mcp_url, client_name="maya-inprocess-http")

        response = mcp_post(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": action, "arguments": {"ping": 1}},
            },
            session_id=session,
        )
        assert "result" in response, response
        payload = _extract_tool_payload(response["result"])
        assert payload.get("success") is True
        assert payload.get("context", {}).get("args", {}).get("ping") == 1

    def test_rest_health_search_and_call(self, echo_maya_server):
        _, handle, action = echo_maya_server
        base = handle.mcp_url().rsplit("/", 1)[0]

        health = rest_get_json(base, "/v1/healthz")
        assert health.get("ok") is True

        search = rest_post_json(base, "/v1/search", {"query": "echo", "loaded_only": True, "limit": 10})
        hits = search.get("hits") or search.get("tools") or []
        assert hits

        called = rest_post_json(
            base,
            "/v1/call",
            {"tool_slug": action, "arguments": {"via": "rest"}},
        )
        output = called.get("output") or called
        if isinstance(output, dict) and "success" in output:
            assert output["success"] is True
        else:
            assert called


@pytest.fixture
def sidecar_mcp_url(echo_maya_server, tmp_path):
    """Sidecar MCP URL registered in FileRegistry (minimal MCP surface)."""
    server, _, action = echo_maya_server
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    port = allocate_ephemeral_port()
    qt_stub = QtJsonLineStubServer(port, server_lookup=lambda: server)
    qt_stub.start()
    surrogate = ParentSurrogate()
    handle = None
    try:
        handle = start_sidecar(
            maya_pid=surrogate.pid,
            qt_port_override=port,
            registry_dir=registry_dir,
            start_qt_server_fn=qt_stub_factory(port),
            stop_qt_server_fn=qt_stub.stop,
            extra_env={"DCC_MCP_GATEWAY_PORT": "0"},
        )
        entry = wait_for_sidecar_registry_row(registry_dir)
        url = mcp_url_from_registry_entry(entry)
        time.sleep(0.1)
        yield url, action, handle, surrogate, qt_stub
    finally:
        surrogate.kill()
        if handle is not None:
            stop_sidecar(handle, stop_qt_server_fn=qt_stub.stop)
        qt_stub.stop()


@pytest.mark.skipif(
    not sidecar_binary_available(),
    reason="dcc-mcp-server binary not available (pip install dcc-mcp-server)",
)
class TestSidecarHttpApi:
    """MCP HTTP on the out-of-process sidecar (dispatch-only surface)."""

    def test_sidecar_mcp_initialize(self, sidecar_mcp_url):
        url, _, _, _, _ = sidecar_mcp_url
        init = mcp_post(
            url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "maya-sidecar-http", "version": "0"},
                },
            },
        )
        assert init.get("result", {}).get("serverInfo", {}).get("name") == "dcc-mcp-sidecar"

    def test_sidecar_mcp_tools_call_via_qt_dispatch(self, sidecar_mcp_url):
        url, action, _, _, _ = sidecar_mcp_url
        session = mcp_initialize(url, client_name="maya-sidecar-http")
        response = mcp_post(
            url,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": action, "arguments": {"sidecar": True}},
            },
            session_id=session,
        )
        assert "result" in response, response
        payload = _extract_tool_payload(response["result"])
        assert payload.get("success") is True

    def test_sidecar_mcp_tools_list_not_supported(self, sidecar_mcp_url):
        url, _, _, _, _ = sidecar_mcp_url
        session = mcp_initialize(url, client_name="maya-sidecar-http")
        response = mcp_post(
            url,
            {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            session_id=session,
        )
        assert "error" in response
        assert response["error"].get("code") == -32601
