"""Maya commandPort helpers for sidecar mode.

Two responsibilities:

* :func:`allocate_free_port` — ask the OS for an ephemeral TCP port via
  ``bind(("127.0.0.1", 0))`` + ``getsockname()``. Maya's
  ``cmds.commandPort`` does not support port 0 (it would not return the
  chosen port), so we have to pick one ourselves. The brief window
  between releasing the socket and Maya re-binding is acceptable —
  commandPort is local-only and the loopback collision rate is
  negligible. Tests can monkey-patch this when determinism matters.
* :func:`build_host_rpc_uri` — format the URI scheme the sidecar binary
  understands. Kept as a one-liner so the wire format is checked into
  the test surface (and a typo cannot drift silently between Maya and
  the Rust router).

This module is **stdlib only** and contains **no Maya imports** so it
can be exercised by pytest without ``maya.cmds`` being importable.
"""

from __future__ import annotations

import socket

__all__ = [
    "DEFAULT_COMMAND_PORT_HINT",
    "allocate_free_port",
    "build_host_rpc_uri",
]

# Documented default for operators who want a stable, predictable port
# (e.g. when scripting `telnet`-style tests against commandPort by hand).
# Sidecar mode itself does NOT use this constant — it always asks the
# OS for an ephemeral port to avoid clashing with other Maya sessions.
#
# Declared without ``typing.Final`` because Maya 2020 / 2022 ship Python
# 3.7 and ``typing.Final`` only landed in 3.8 (``ImportError`` at plug-in
# load time). Convention (UPPER_SNAKE_CASE) is the immutability marker
# instead — see the Python 3.7 compatibility regression test in
# ``tests/test_python_3_7_compat.py``.
DEFAULT_COMMAND_PORT_HINT = 6000


def allocate_free_port(host: str = "127.0.0.1") -> int:
    """Return an OS-assigned ephemeral TCP port on ``host``.

    Args:
        host: bind address to probe against. Defaults to loopback so
            the port number is exclusively for same-machine use.

    Returns:
        An integer in the ephemeral port range that was free at the
        moment ``getsockname`` was called. The caller is responsible
        for handing it to ``cmds.commandPort`` promptly — there is a
        small race window where another process could grab it.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def build_host_rpc_uri(port: int, host: str = "127.0.0.1") -> str:
    """Format the ``commandport://`` URI the sidecar uses to dial back.

    The scheme is the discriminator the Rust router in
    ``dcc-mcp-server`` will eventually match on to pick the
    ``HostRpcClient`` impl. Keep it lowercase and stable.

    Args:
        port: TCP port on which Maya's ``commandPort`` is listening.
        host: bind address Maya advertises. Defaults to loopback.

    Returns:
        A URI of the form ``"commandport://127.0.0.1:6042"``.
    """
    if port <= 0 or port > 65535:
        raise ValueError(f"port must be in 1..65535, got {port}")
    return f"commandport://{host}:{port}"
