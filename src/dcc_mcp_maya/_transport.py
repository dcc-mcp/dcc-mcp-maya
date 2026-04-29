"""Maya-specific :class:`TransportManager` wrappers (issue #127).

Three thin helpers extracted from ``server.py``:

* :func:`bind_and_register` — auto-detects the Maya version and forwards
  to ``TransportManager.bind_and_register``.
* :func:`find_best_service` — wraps ``TransportManager.find_best_service``
  with default ``dcc_type="maya"``.
* :func:`rank_services` — wraps ``TransportManager.rank_services`` and
  always returns a list (never an iterator).

All three swallow the exceptions that the underlying calls can raise so
the server can keep running even when the registry is mid-rotation.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, List, Optional

# Import local modules
from dcc_mcp_maya._version_probe import get_maya_version_string

logger = logging.getLogger(__name__)


def bind_and_register(
    transport_manager: Any,
    version: Optional[str] = None,
    metadata: Optional[Any] = None,
) -> Any:
    """Register this Maya instance via ``TransportManager.bind_and_register``.

    Auto-detects the Maya version when ``version`` is not supplied.

    Returns the ``(instance_id, listener)`` tuple from the underlying
    call, or ``None`` when the call fails (logged at WARNING level).
    """
    if version is None:
        version = get_maya_version_string()
    try:
        return transport_manager.bind_and_register(
            "maya",
            version=version,
            metadata=metadata or {},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("bind_and_register failed: %s", exc)
        return None


def find_best_service(transport_manager: Any, dcc_type: str = "maya") -> Any:
    """Find the best available Maya MCP service.

    Wraps ``TransportManager.find_best_service``.  Returns ``None`` when
    no service is available or the call fails.
    """
    try:
        return transport_manager.find_best_service(dcc_type)
    except Exception as exc:  # noqa: BLE001
        logger.debug("find_best_service failed: %s", exc)
        return None


def rank_services(transport_manager: Any, dcc_type: str = "maya") -> List[Any]:
    """Rank all active Maya MCP instances.

    Wraps ``TransportManager.rank_services`` and converts the result to
    a list so callers can iterate freely.  Returns ``[]`` on failure.
    """
    try:
        return list(transport_manager.rank_services(dcc_type))
    except Exception as exc:  # noqa: BLE001
        logger.debug("rank_services failed: %s", exc)
        return []
