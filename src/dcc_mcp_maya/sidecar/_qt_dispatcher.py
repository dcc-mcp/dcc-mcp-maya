r"""Universal in-DCC JSON-line TCP dispatcher driven by the Qt event loop.

.. note::

   **Vendored** from ``dcc-mcp-core`` at
   ``crates/dcc-mcp-host-rpc/python/dcc_qt_dispatcher.py``. The
   canonical source lives upstream; this is a byte-for-byte copy with
   only the docstring header extended (this very note). Keep both in
   sync — the upstream file is the wire-format authority shipped over
   the Rust sidecar binary via ``include_str!``, and the Maya plug-in
   imports this copy directly so it can start a Qt server without
   waiting for the sidecar binary to inject the source.

   When a new ``dcc-mcp-core`` release ships the dispatcher as a real
   public Python module (``dcc_mcp_core.qt_dispatcher``), this file
   gets replaced with a one-line ``from dcc_mcp_core.qt_dispatcher
   import *`` re-export. Until then, refresh manually:

   .. code-block:: powershell

      Copy-Item ..\\dcc-mcp-core\\crates\\dcc-mcp-host-rpc\\python\\dcc_qt_dispatcher.py `
                src\\dcc_mcp_maya\\sidecar\\_qt_dispatcher.py


The same module installs into Maya, Houdini, 3ds Max, Nuke, Cinema 4D,
Substance Painter, Mari — any DCC that ships a Qt binding (PySide2 /
PySide6 / PyQt5 / PyQt6 are all probed). The Rust sidecar speaks to
this server over the ``qtserver://`` URI scheme defined in
``dcc_mcp_host_rpc::qtserver``.

Why this design solves the in-DCC fragility problems
====================================================

The previous baseline (``commandPort`` + line-oriented Python eval) had
three structural failure modes that no amount of plug-in hardening
could fully paper over:

1. **Single-flight** — one in-flight request at a time per port; a
   slow request blocks every other gateway caller.
2. **Modal dialog leak** — any uncaught Python exception inside the
   eval bubbles up to ``maya.utils.executeDeferred`` / DCC dialog
   code, freezing the UI on a "File error" or "Stack trace" modal.
3. **PyO3-tokio runtime contention** — the embedded MCP HTTP server
   competes with the DCC's main thread for scheduler attention.

Running an in-DCC ``QTcpServer`` cooperatively on the host's Qt event
loop addresses all three:

* ``QTcpServer`` accepts many concurrent connections; each connection
  is a small per-socket state machine driven by ``readyRead`` signals.
* Every request is wrapped in a single per-handler ``try/except`` —
  failures return a structured JSON envelope, never propagate to
  dialog code.
* The dispatcher runs on the DCC's own main thread (the only thread
  that can safely touch the host scene), but it gives that thread
  *up* between requests via the standard Qt event-loop tick. The
  Rust sidecar has its own tokio runtime and never competes.

Wire protocol
=============

One JSON object per ``\\n``-terminated line in each direction.

Request::

    {"id": "req-1", "method": "execute", "params": {"code": "1+2"}}

Successful response::

    {"id": "req-1", "result": {"value": 3}}

Error response::

    {"id": "req-1",
     "error": {"code": "handler-exception",
               "message": "ZeroDivisionError: division by zero",
               "traceback": "Traceback (...)"}}

Built-in handlers
=================

``ping``
    Cheap health check. Returns ``{"pong": True, "version": ...}``.

``execute``
    Runs arbitrary Python via :func:`ast.parse` + :func:`compile`. If
    the source ends in an expression statement, that expression is
    evaluated as the result; everything before runs as a side-effect
    body. ``params.result_type`` selects between ``"value"`` (default,
    JSON-serialisable representation) and ``"repr"`` (``repr(value)``)
    for non-JSON-serialisable objects.

``get_session_info``
    Returns Python version, executable path, Qt binding name, and the
    dispatcher version string.

``install_stream_capture`` / ``get_buffered_output``
    Tee ``sys.stdout`` / ``sys.stderr`` into an internal buffer so
    follow-up calls can read everything the DCC printed (Maya
    "Script Editor" output, ``print`` statements, etc.).

``create_module``
    Synthesise a Python module from a source string. Used so the
    sidecar can install per-DCC dispatcher extensions (Maya-specific
    helpers, Houdini ``hou`` wrappers, …) without requiring a
    ``.py`` file on disk. Idempotent on ``version`` match.
"""


# JSON envelope; broad ``except`` is the whole point of this dispatcher.

import ast
import contextlib
import io
import json
import sys
import threading
import traceback
import types

DISPATCHER_VERSION = "1"

# Tracks the singleton server so :func:`start_qt_server` is idempotent
# and the bootstrap path can reconnect to an existing instance.
_singleton: dict = {"server": None}
_singleton_lock = threading.Lock()


def _import_qt():
    """Return ``(QtCore, QtNetwork, binding_name)`` using the first Qt binding that loads.

    Order is PySide6 → PySide2 → PyQt6 → PyQt5 so newer DCCs (Maya
    2024+, Houdini 20+) prefer PySide6 while older ones (Maya
    2022/2023) fall back to PySide2.
    """
    last_error = None
    for module_name in ("PySide6", "PySide2", "PyQt6", "PyQt5"):
        try:
            qt_core = __import__(module_name + ".QtCore", fromlist=["QtCore"])
            qt_network = __import__(module_name + ".QtNetwork", fromlist=["QtNetwork"])
            return qt_core, qt_network, module_name
        except ImportError as exc:
            last_error = exc
            continue
    raise ImportError(f"no Qt binding available — tried PySide6/PySide2/PyQt6/PyQt5; last error: {last_error}")


class _Tee:
    """Tee a write stream to many sinks.

    Tolerates broken sinks so a closed DCC console can never break a
    buffered-output read.
    """

    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for stream in self._streams:
            with contextlib.suppress(Exception):
                stream.write(data)

    def flush(self):
        for stream in self._streams:
            with contextlib.suppress(Exception):
                stream.flush()

    def isatty(self):
        return False


class _DispatchRegistry:
    """Mutable per-server registry of method handlers.

    Lives outside :class:`QtCommandServer` so the dispatch table can be
    unit-tested in isolation (no Qt event loop required) and so a
    fresh server instance always starts from a deterministic baseline.
    """

    def __init__(self):
        self._handlers = {
            "ping": self._ping,
            "execute": self._execute,
            "get_session_info": self._get_session_info,
            "install_stream_capture": self._install_stream_capture,
            "get_buffered_output": self._get_buffered_output,
            "create_module": self._create_module,
        }
        self._exec_globals: dict = {"__name__": "__dcc_qt_dispatcher__"}
        self._captured = io.StringIO()
        self._capture_active = False
        self._stdout_orig = sys.stdout
        self._stderr_orig = sys.stderr

    def register(self, method, handler):
        """Install an extension handler.

        Used by tests and adapter bootstrap so DCC-specific methods
        can ride the same wire.
        """
        self._handlers[method] = handler

    def dispatch(self, method, params):
        """Look up ``method``, invoke its handler with ``params``, return an envelope.

        The outcome is wrapped in a ``{"result": ...}`` or
        ``{"error": ...}`` envelope. Never raises.
        """
        handler = self._handlers.get(method)
        if handler is None:
            return {
                "error": {
                    "code": "unknown-method",
                    "message": f"unknown method {method!r}",
                }
            }
        try:
            return {"result": handler(params or {})}
        except Exception as exc:
            return {
                "error": {
                    "code": "handler-exception",
                    "message": f"{exc.__class__.__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                }
            }

    # ── builtin handlers ───────────────────────────────────────────

    def _ping(self, _params):
        return {"pong": True, "version": DISPATCHER_VERSION}

    def _execute(self, params):
        code = params.get("code", "")
        if not isinstance(code, str):
            raise TypeError("`code` must be a string")
        result_type = (params.get("result_type") or "value").lower()
        tree = ast.parse(code, filename="<dcc-execute>", mode="exec")
        last_expr = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = tree.body[-1].value
            tree.body = tree.body[:-1]
        exec(
            compile(tree, "<dcc-execute>", "exec"),
            self._exec_globals,
        )
        if last_expr is None:
            return {"value": None, "result_type": "void"}
        value = eval(
            compile(ast.Expression(body=last_expr), "<dcc-execute>", "eval"),
            self._exec_globals,
        )
        if result_type == "repr":
            return {"value": repr(value), "result_type": "repr"}
        # default "value": be liberal — fall back to repr for objects
        # that aren't JSON-serialisable so the gateway never sees a
        # serialisation error from this surface.
        try:
            json.dumps(value)
            serialised = value
        except (TypeError, ValueError):
            serialised = repr(value)
        return {"value": serialised, "result_type": "value"}

    def _get_session_info(self, _params):
        return {
            "python_version": sys.version,
            "executable": sys.executable,
            "platform": sys.platform,
            "dispatcher_version": DISPATCHER_VERSION,
        }

    def _install_stream_capture(self, _params):
        if self._capture_active:
            return {"installed": False, "reused": True}
        self._captured = io.StringIO()
        sys.stdout = _Tee(self._stdout_orig, self._captured)
        sys.stderr = _Tee(self._stderr_orig, self._captured)
        self._capture_active = True
        return {"installed": True}

    def _get_buffered_output(self, params):
        text = self._captured.getvalue()
        if params.get("drain", True):
            self._captured = io.StringIO()
            if self._capture_active:
                sys.stdout = _Tee(self._stdout_orig, self._captured)
                sys.stderr = _Tee(self._stderr_orig, self._captured)
        return {"output": text}

    def _create_module(self, params):
        name = params.get("name")
        source = params.get("source")
        if not isinstance(name, str) or not name:
            raise ValueError("`name` must be a non-empty string")
        if not isinstance(source, str):
            raise TypeError("`source` must be a string")
        version = params.get("version") or ""
        existing = sys.modules.get(name)
        if existing is not None and getattr(existing, "__dcc_mcp_module_version__", None) == version and version:
            return {"installed": False, "reused": True, "name": name, "version": version}
        module = types.ModuleType(name)
        module.__file__ = f"<dcc-mcp-create-module:{name}>"
        if version:
            module.__dcc_mcp_module_version__ = version
        exec(
            compile(source, module.__file__, "exec"),
            module.__dict__,
        )
        sys.modules[name] = module
        return {"installed": True, "name": name, "version": version}


class QtCommandServer:
    r"""JSON-line ``QTcpServer`` cooperatively scheduled on the Qt main thread.

    Multi-client; per-connection ``bytearray`` buffers accumulate
    incoming bytes until a ``\n`` boundary, at which point one full
    request is dispatched.
    """

    def __init__(self, port=0, host="127.0.0.1"):
        qt_core, qt_network, binding = _import_qt()
        self._QtCore = qt_core
        self._QtNetwork = qt_network
        self._qt_binding = binding
        self._server = qt_network.QTcpServer()
        addr = qt_network.QHostAddress(host)
        if not self._server.listen(addr, port):
            raise RuntimeError(f"QTcpServer.listen({host}:{port}) failed: {self._server.errorString()}")
        self._actual_host = host
        self._actual_port = int(self._server.serverPort())
        self._registry = _DispatchRegistry()
        self._clients: dict = {}
        self._server.newConnection.connect(self._on_new_connection)
        self._timer = qt_core.QTimer()
        self._timer.timeout.connect(self._drain_all)
        self._timer.start(50)

    @property
    def host(self):
        return self._actual_host

    @property
    def port(self):
        return self._actual_port

    @property
    def qt_binding(self):
        return self._qt_binding

    @property
    def registry(self):
        return self._registry

    def stop(self):
        with contextlib.suppress(Exception):
            self._timer.stop()
        for sock in list(self._clients):
            with contextlib.suppress(Exception):
                sock.disconnectFromHost()
        self._clients.clear()
        with contextlib.suppress(Exception):
            self._server.close()

    def _on_new_connection(self):
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            self._clients[sock] = bytearray()
            sock.readyRead.connect(lambda bound=sock: self._on_ready_read(bound))
            sock.disconnected.connect(lambda bound=sock: self._on_disconnected(bound))

    def _on_disconnected(self, sock):
        self._clients.pop(sock, None)
        with contextlib.suppress(Exception):
            sock.deleteLater()

    def _on_ready_read(self, sock):
        if sock not in self._clients:
            return
        try:
            chunk = bytes(sock.readAll())
        except Exception:
            return
        if not chunk:
            return
        buffer = self._clients[sock]
        buffer.extend(chunk)
        while True:
            try:
                idx = buffer.index(0x0A)  # newline byte
            except ValueError:
                break
            line = bytes(buffer[:idx])
            del buffer[: idx + 1]
            if line.endswith(b"\r"):
                line = line[:-1]
            self._handle_line(sock, line)

    def _drain_all(self):
        for sock in list(self._clients):
            try:
                if sock.bytesAvailable() > 0:
                    self._on_ready_read(sock)
            except Exception:
                pass

    def _handle_line(self, sock, raw):
        try:
            request = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send(
                sock,
                {
                    "id": None,
                    "error": {
                        "code": "parse-error",
                        "message": f"{exc.__class__.__name__}: {exc}",
                    },
                },
            )
            return
        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params") or {}
        outcome = self._registry.dispatch(method, params)
        payload = {"id": request_id}
        payload.update(outcome)
        self._send(sock, payload)

    def _send(self, sock, payload):
        try:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as exc:
            # Re-encode failure to a parse-error so the wire never
            # gets stuck mid-message.
            encoded = (
                json.dumps(
                    {
                        "id": payload.get("id"),
                        "error": {
                            "code": "encode-error",
                            "message": f"{exc.__class__.__name__}: {exc}",
                        },
                    }
                ).encode("utf-8")
                + b"\n"
            )
        try:
            sock.write(encoded)
            sock.flush()
        except Exception:
            # Best-effort write — a closed socket is removed by the
            # ``disconnected`` signal handler and we should not poison
            # the dispatcher with a console traceback.
            pass


def start_qt_server(port=0, host="127.0.0.1"):
    """Start (or reuse) the singleton :class:`QtCommandServer`.

    Returns a small dict ``{"host": str, "port": int, "qt_binding": str,
    "dispatcher_version": str, "reused": bool}`` so the caller can
    learn the actually-bound ephemeral port. Idempotent — repeated
    calls return the running server's info.
    """
    with _singleton_lock:
        server = _singleton["server"]
        reused = server is not None
        if not reused:
            server = QtCommandServer(port=port, host=host)
            _singleton["server"] = server
    return {
        "host": server.host,
        "port": server.port,
        "qt_binding": server.qt_binding,
        "dispatcher_version": DISPATCHER_VERSION,
        "reused": reused,
    }


def stop_qt_server():
    """Tear down the singleton server, if any. Idempotent."""
    with _singleton_lock:
        server = _singleton.pop("server", None)
    if server is not None:
        server.stop()
    return {"stopped": server is not None}


def current_server():
    """Return the singleton server instance, or ``None``.

    Public so Maya plug-ins can introspect runtime state for
    diagnostics.
    """
    return _singleton.get("server")
