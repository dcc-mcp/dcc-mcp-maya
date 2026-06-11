"""Gateway runtime env wiring tests."""

from __future__ import annotations

from pathlib import Path

from dcc_mcp_maya._gateway_runtime import ensure_gateway_server_binary_env
from dcc_mcp_maya.sidecar._resolver import ENV_SIDECAR_BINARY, SidecarBinaryError


def test_ensure_gateway_server_binary_env_sets_resolved_binary() -> None:
    env: dict[str, str] = {}
    binary = Path("/opt/dcc-mcp/bin/dcc-mcp-server")

    changed = ensure_gateway_server_binary_env(
        env=env,
        resolver=lambda: binary,
    )

    assert changed is True
    assert env[ENV_SIDECAR_BINARY] == str(binary)


def test_ensure_gateway_server_binary_env_respects_explicit_override() -> None:
    env = {ENV_SIDECAR_BINARY: "/custom/dcc-mcp-server"}
    called = False

    def resolver() -> Path:
        nonlocal called
        called = True
        return Path("/other/dcc-mcp-server")

    changed = ensure_gateway_server_binary_env(env=env, resolver=resolver)

    assert changed is False
    assert called is False
    assert env[ENV_SIDECAR_BINARY] == "/custom/dcc-mcp-server"


def test_ensure_gateway_server_binary_env_is_best_effort_when_missing() -> None:
    env: dict[str, str] = {}

    def resolver() -> Path:
        raise SidecarBinaryError("missing")

    changed = ensure_gateway_server_binary_env(env=env, resolver=resolver)

    assert changed is False
    assert ENV_SIDECAR_BINARY not in env
