"""Best-effort cleanup for dcc-mcp log files."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 14
DEFAULT_MAX_TOTAL_SIZE_MB = 200


def prune_maya_logs(
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    max_total_size_mb: int = DEFAULT_MAX_TOTAL_SIZE_MB,
) -> Optional[object]:
    """Prune old dcc-mcp log files when core exposes log retention.

    ``dcc-mcp-core`` 0.15.8 exports ``prune_old_logs``.  Older local test
    environments may not have it yet, so this helper is intentionally a no-op
    when the symbol is absent.
    """
    try:
        from dcc_mcp_core import prune_old_logs  # noqa: PLC0415
    except ImportError:
        logger.debug("log pruning unavailable: dcc_mcp_core.prune_old_logs missing")
        return None

    try:
        return prune_old_logs(
            retention_days=retention_days,
            max_total_size_mb=max_total_size_mb,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("log pruning failed: %s", exc)
        return None
