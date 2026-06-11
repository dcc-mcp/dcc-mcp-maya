"""Gateway runtime wiring for Maya's embedded server path."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable, MutableMapping, Optional

from dcc_mcp_maya.sidecar._resolver import ENV_SIDECAR_BINARY, SidecarBinaryError, resolve_sidecar_binary

logger = logging.getLogger(__name__)


def ensure_gateway_server_binary_env(
    *,
    env: Optional[MutableMapping[str, str]] = None,
    resolver: Callable[[], Path] = resolve_sidecar_binary,
) -> bool:
    """Expose Maya's packaged ``dcc-mcp-server`` binary to core.

    ``dcc-mcp-core`` starts the standalone gateway daemon from
    ``DCC_MCP_SERVER_BIN`` or ``PATH``.  Maya module ZIPs bundle the
    ``dcc_mcp_server`` package under ``python/`` and its executable under
    ``python/scripts/``; that location is importable but not necessarily on
    ``PATH``.  Bridge the two contracts before calling core startup.

    Returns ``True`` when this function set the env var.
    """
    target_env = os.environ if env is None else env
    if target_env.get(ENV_SIDECAR_BINARY):
        return False

    try:
        binary = resolver()
    except SidecarBinaryError as exc:
        logger.debug("gateway runtime binary not configured: %s", exc)
        return False

    target_env[ENV_SIDECAR_BINARY] = str(binary)
    logger.debug("gateway runtime binary configured via %s=%s", ENV_SIDECAR_BINARY, binary)
    return True
