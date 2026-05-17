"""Shared helpers for Maya HTTP / sidecar transport tests."""

from __future__ import annotations

import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

from dcc_mcp_maya.sidecar._resolver import SidecarBinaryError, resolve_sidecar_binary

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

os.environ.setdefault("DCC_MCP_DISABLE_FILE_LOGGING", "1")
os.environ.setdefault("DCC_MCP_ALLOW_AMBIENT_PYTHON", "1")


def sidecar_binary_available() -> bool:
    try:
        resolve_sidecar_binary()
        return True
    except SidecarBinaryError:
        return False


def allocate_ephemeral_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def mcp_post(
    mcp_url: str,
    payload: Dict[str, Any],
    *,
    session_id: Optional[str] = None,
    expect_response: bool = True,
) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(
        mcp_url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
        session_out = resp.headers.get("Mcp-Session-Id")
        status = resp.status
    if not expect_response:
        return {"__status__": status, "__session_id__": session_out}
    text = body.decode("utf-8", errors="replace").strip()
    if text.startswith("event:") or "\n\ndata: " in text or text.startswith("data: "):
        for line in text.splitlines():
            if line.startswith("data: "):
                text = line[len("data: ") :]
                break
    parsed = json.loads(text) if text else {}
    parsed["__session_id__"] = session_out
    parsed["__status__"] = status
    return parsed


def mcp_initialize(mcp_url: str, *, client_name: str = "maya-transport-test") -> str:
    init = mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": "0"},
            },
        },
    )
    session_id = init.get("__session_id__")
    mcp_post(
        mcp_url,
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        session_id=session_id,
        expect_response=False,
    )
    return session_id


def rest_get_json(base_url: str, endpoint: str) -> Dict[str, Any]:
    with urllib.request.urlopen(base_url + endpoint, timeout=10) as resp:
        assert resp.status == 200
        return json.loads(resp.read() or b"{}")


def rest_post_json(base_url: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(
        base_url + endpoint,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        assert resp.status == 200
        return json.loads(resp.read() or b"{}")


def wait_for_sidecar_registry_row(registry_dir: Path, timeout: float = 8.0) -> Dict[str, Any]:
    services_path = registry_dir / "services.json"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if services_path.is_file():
            payload = json.loads(services_path.read_text(encoding="utf-8"))
            for entry in _iter_registry_entries(payload):
                metadata = entry.get("metadata") or {}
                if metadata.get("dcc_mcp_role") == "per-dcc-sidecar":
                    return entry
        time.sleep(0.05)
    raise AssertionError("per-dcc-sidecar FileRegistry row never appeared in {}".format(services_path))


def mcp_url_from_registry_entry(entry: Dict[str, Any]) -> str:
    metadata = entry.get("metadata") or {}
    url = metadata.get("mcp_url")
    if isinstance(url, str) and url:
        return url
    host = entry.get("host") or "127.0.0.1"
    port = entry.get("port")
    if port is not None:
        return "http://{}:{}/mcp".format(host, port)
    raise AssertionError("registry entry has no mcp_url: {}".format(entry))


def _iter_registry_entries(payload: object) -> Iterator[Dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
    elif isinstance(payload, dict):
        services = payload.get("services")
        if isinstance(services, list):
            for item in services:
                if isinstance(item, dict):
                    yield item
        elif isinstance(services, dict):
            for item in services.values():
                if isinstance(item, dict):
                    yield item
        else:
            for value in payload.values():
                if isinstance(value, dict) and "dcc_type" in value:
                    yield value


class ParentSurrogate:
    """Stand-in for Maya's PID for sidecar ``--watch-pid``."""

    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(300)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @property
    def pid(self) -> int:
        return self.proc.pid

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)


class QtJsonLineStubServer:
    """Minimal ``qtserver://`` peer that forwards ``dispatch`` to Maya."""

    def __init__(self, port: int, *, server_lookup: Callable[[], Any]) -> None:
        from dcc_mcp_maya.sidecar._dispatcher import dispatch_payload

        self._port = port
        self._dispatch_payload = dispatch_payload
        self._server_lookup = server_lookup
        self._httpd: Optional[socketserver.ThreadingTCPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        parent = self

        class _Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                buffer = b""
                self.request.settimeout(2.0)
                while True:
                    try:
                        chunk = self.request.recv(4096)
                    except (OSError, socket.timeout):
                        return
                    if not chunk:
                        return
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        reply = parent._handle_line(line.decode("utf-8", errors="replace").strip())
                        if reply:
                            self.request.sendall((reply + "\n").encode("utf-8"))

        self._httpd = socketserver.ThreadingTCPServer(("127.0.0.1", self._port), _Handler)
        self._httpd.daemon_threads = True
        self._httpd.allow_reuse_address = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _handle_line(self, line: str) -> str:
        if not line:
            return ""
        request = json.loads(line)
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        if method == "ping":
            return json.dumps(
                {"id": req_id, "result": {"pong": True, "version": "maya-test-stub"}},
                ensure_ascii=False,
            )
        if method == "dispatch":
            raw = self._dispatch_payload(
                {
                    "action": params.get("action"),
                    "args": params.get("args") or {},
                    "request_id": params.get("request_id") or str(req_id or ""),
                },
                server_lookup=self._server_lookup,
            )
            return json.dumps({"id": req_id, "result": json.loads(raw)}, ensure_ascii=False)
        return json.dumps(
            {
                "id": req_id,
                "error": {"code": "unknown-method", "message": "unsupported method {!r}".format(method)},
            },
            ensure_ascii=False,
        )


def qt_stub_factory(port: int) -> Callable[..., Dict[str, Any]]:
    def _stub(port: int = 0, host: str = "127.0.0.1") -> Dict[str, Any]:
        return {
            "host": host,
            "port": port or qt_stub_factory._announced_port,
            "qt_binding": "test-json-line-stub",
            "dispatcher_version": "1",
            "reused": False,
        }

    qt_stub_factory._announced_port = port  # type: ignore[attr-defined]
    return _stub
