"""Environment-variable resolution for ``MayaMcpServer`` (issue #127).

Centralises every ``DCC_MCP_MAYA_*`` env var used by the server so the
composition root in :mod:`dcc_mcp_maya.server` stays a thin orchestrator.

All helpers are pure functions: they read :data:`os.environ` and return
plain Python values; they never mutate global state.

See: https://github.com/loonghao/dcc-mcp-maya/issues/127
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Public env-var names ─────────────────────────────────────────────────────
ENV_MINIMAL = "DCC_MCP_MAYA_MINIMAL"
ENV_DEFAULT_TOOLS = "DCC_MCP_MAYA_DEFAULT_TOOLS"
ENV_METRICS = "DCC_MCP_MAYA_METRICS"
ENV_JOB_STORAGE = "DCC_MCP_MAYA_JOB_STORAGE"
ENV_JOB_RECOVERY = "DCC_MCP_MAYA_JOB_RECOVERY"
ENV_WINDOW_TITLE = "DCC_MCP_MAYA_WINDOW_TITLE"
#: Issue #138 — when set to ``"1"``, ``register_builtin_actions`` runs
#: :func:`dcc_mcp_core.scan_and_load_strict` after discovery so any
#: silently-skipped skill directory raises ``ValueError`` at startup
#: instead of disappearing into a debug-level log line.
ENV_STRICT_SKILL_SCAN = "DCC_MCP_MAYA_STRICT_SKILL_SCAN"

#: Default SQLite filename inside the platform data directory.
DEFAULT_JOB_DB_FILENAME = "jobs.db"


def resolve_minimal_flag(minimal: Optional[bool]) -> bool:
    """Resolve the minimal-mode flag from argument and env var.

    Priority order:

    1. Explicit ``minimal`` argument (when not ``None``).
    2. ``DCC_MCP_MAYA_MINIMAL`` env var: ``"0"`` → ``False``, anything
       else (including ``"1"``) → ``True``.
    3. Default: ``True``.
    """
    if minimal is not None:
        return minimal
    env_val = os.environ.get(ENV_MINIMAL)
    if env_val is not None:
        return env_val.strip() != "0"
    return True


def resolve_default_tools() -> Optional[Dict[str, List[str]]]:
    """Parse ``DCC_MCP_MAYA_DEFAULT_TOOLS`` into a ``{skill: [groups]}`` map.

    Format: comma-separated list of skill names.  When set, only the
    listed skills are loaded at startup.  Returns ``None`` when the env
    var is unset or empty.
    """
    raw = os.environ.get(ENV_DEFAULT_TOOLS)
    if not raw:
        return None
    result: Dict[str, List[str]] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        result.setdefault(token, [])
    return result


def resolve_metrics_enabled(metrics_enabled: Optional[bool]) -> bool:
    """Resolve the Prometheus ``/metrics`` endpoint flag.

    Priority: explicit argument > ``DCC_MCP_MAYA_METRICS=1`` > ``False``.
    """
    if metrics_enabled is not None:
        return bool(metrics_enabled)
    return os.environ.get(ENV_METRICS, "").strip() == "1"


def resolve_job_storage(job_storage_path: Optional[str]) -> Optional[str]:
    """Resolve the SQLite job-storage path.

    Returns ``None`` when callers should leave whatever path
    :class:`DccServerBase._init_job_persistence` selected.  Returns the
    empty string ``""`` when the caller passed ``""`` explicitly to
    request in-memory operation (no persistence).

    Priority order:

    1. Explicit ``job_storage_path`` argument (when not ``None``).  An
       empty string preserves the empty intent.
    2. ``DCC_MCP_MAYA_JOB_STORAGE`` env var.
    3. ``<platform_data_dir>/dcc-mcp-maya/jobs.db`` (auto-created).
    """
    if job_storage_path is not None:
        if not str(job_storage_path).strip():
            return ""  # explicit "disable persistence"
        return job_storage_path

    env_val = os.environ.get(ENV_JOB_STORAGE)
    if env_val is not None:
        return env_val

    try:
        from dcc_mcp_core import get_data_dir  # noqa: PLC0415

        data_dir = Path(get_data_dir()) / "dcc-mcp-maya"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir / DEFAULT_JOB_DB_FILENAME)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not resolve default job storage path: %s", exc)
        return None


def resolve_job_recovery(job_recovery: Optional[str]) -> str:
    """Resolve the interrupted-job recovery policy.

    Returns either ``"drop"`` (default — discard interrupted jobs) or
    ``"requeue"`` (re-submit idempotent jobs on startup).  Any other
    value (including a malformed env var) collapses to ``"drop"`` so the
    server never starts in an undefined state.

    Priority: explicit argument > ``DCC_MCP_MAYA_JOB_RECOVERY`` > ``"drop"``.
    """
    raw: Optional[str]
    if job_recovery is not None:
        raw = job_recovery
    else:
        raw = os.environ.get(ENV_JOB_RECOVERY, "drop")
    normalised = (raw or "drop").strip().lower()
    return normalised if normalised in ("drop", "requeue") else "drop"


def resolve_window_title(dcc_window_title: Optional[str]) -> Optional[str]:
    """Resolve the diagnostics-screenshot window-title hint."""
    if dcc_window_title is not None:
        return dcc_window_title
    raw = os.environ.get(ENV_WINDOW_TITLE, "").strip()
    return raw or None


def resolve_strict_skill_scan(strict: Optional[bool] = None) -> bool:
    """Resolve whether to run :func:`scan_and_load_strict` after discovery.

    Issue #138 acceptance criterion: a ``--strict`` knob so CI can fail
    when skill packages don't validate (today they silently disappear).

    Priority: explicit ``strict`` argument > ``DCC_MCP_MAYA_STRICT_SKILL_SCAN=1``
    > ``False``.
    """
    if strict is not None:
        return bool(strict)
    return os.environ.get(ENV_STRICT_SKILL_SCAN, "").strip() == "1"


# Backwards-compatibility aliases — the leading-underscore names mirror the
# previous module-private constants in ``server.py`` so any unit test or
# downstream patcher that reaches in still works.
_ENV_MINIMAL = ENV_MINIMAL
_ENV_DEFAULT_TOOLS = ENV_DEFAULT_TOOLS
_ENV_METRICS = ENV_METRICS
_ENV_JOB_STORAGE = ENV_JOB_STORAGE
_ENV_JOB_RECOVERY = ENV_JOB_RECOVERY
_DEFAULT_JOB_DB_FILENAME = DEFAULT_JOB_DB_FILENAME


def _unused_marker(_value: Any) -> None:  # pragma: no cover
    """Sentinel referencing :data:`Any` so the type-only import is retained."""
    return None
