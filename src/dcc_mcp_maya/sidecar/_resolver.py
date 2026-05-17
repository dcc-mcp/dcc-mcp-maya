"""Locate the ``dcc-mcp-server`` Rust binary that powers sidecar mode.

Resolution order (first match wins):

1. ``DCC_MCP_SERVER_BIN`` env var — operator override. Useful for dev
   builds where the binary lives outside any installed package.
2. ``from dcc_mcp_server import binary_path`` — the ``dcc-mcp-server``
   PyPI wheel installs a tiny Python locator alongside the binary.
3. ``shutil.which("dcc-mcp-server")`` — any binary on ``PATH`` (covers
   ``cargo install``, OS package managers, etc.).
4. Fallback: raise :class:`SidecarBinaryError`.

This module is **stdlib only** so it can be imported from the Maya
plug-in entry point before any heavyweight dependency is loaded.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

__all__ = [
    "ENV_SIDECAR_BINARY",
    "SidecarBinaryError",
    "resolve_sidecar_binary",
]

logger = logging.getLogger(__name__)

ENV_SIDECAR_BINARY = "DCC_MCP_SERVER_BIN"


class SidecarBinaryError(RuntimeError):
    """Raised when the ``dcc-mcp-server`` binary cannot be located."""


def resolve_sidecar_binary() -> Path:
    """Return the absolute path of the ``dcc-mcp-server`` binary.

    Raises:
        SidecarBinaryError: when no installation is found anywhere on the
            search path. The message lists every location that was probed
            so operators can diagnose without re-running with extra logs.
    """
    probed: list[str] = []

    override = os.environ.get(ENV_SIDECAR_BINARY)
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            logger.debug("sidecar binary resolved via %s=%s", ENV_SIDECAR_BINARY, candidate)
            return candidate
        raise SidecarBinaryError(
            "Could not locate the dcc-mcp-server binary. Explicit "
            + ENV_SIDECAR_BINARY
            + " override is not a file: "
            + override
        )

    try:
        from dcc_mcp_server import binary_path  # type: ignore[import-not-found]

        candidate = Path(binary_path())
        if candidate.is_file():
            logger.debug("sidecar binary resolved via dcc_mcp_server.binary_path()=%s", candidate)
            return candidate
        probed.append(f"dcc_mcp_server.binary_path()={candidate} (not a file)")
    except ImportError as exc:
        probed.append(f"dcc_mcp_server package not importable ({exc})")
    except FileNotFoundError as exc:
        # binary_path() itself raises this when its own search fails;
        # forward the message for diagnostics.
        probed.append(f"dcc_mcp_server.binary_path() raised: {exc}")

    on_path = shutil.which("dcc-mcp-server")
    if on_path:
        candidate = Path(on_path)
        logger.debug("sidecar binary resolved via PATH lookup=%s", candidate)
        return candidate
    probed.append('shutil.which("dcc-mcp-server") returned None')

    raise SidecarBinaryError(
        "Could not locate the dcc-mcp-server binary. Probed:\n  - "
        + "\n  - ".join(probed)
        + "\nInstall via `pip install dcc-mcp-server`, set "
        + ENV_SIDECAR_BINARY
        + " to an explicit path, or put the binary on PATH."
    )
