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
#: Issue #139 / dcc-mcp-core#565 — opt-in workflow engine surface
#: (``workflows.run``, ``workflows.resume``, ``workflows.list_runs`` MCP
#: tools).  Off by default so the minimal-mode tools/list stays small.
ENV_ENABLE_WORKFLOWS = "DCC_MCP_MAYA_ENABLE_WORKFLOWS"
#: dcc-mcp-core#652 (0.14.22) — opt-in gateway ``tools/list`` shaping.
#: Accepted values: ``"full"`` (default — every backend tool fanned out),
#: ``"slim"`` (gateway meta-tools only, backend reached via
#: ``search_tools``/``call_tool``), ``"rest"`` (same as slim in
#: ``tools/list``; backend lives on the per-DCC ``/v1/*`` surface), or
#: ``"both"`` (transitional alias of ``"full"`` that keeps
#: compatibility-layer semantics explicit).  Anything else falls back to
#: ``"full"`` and logs a warning so a typo never kills startup.
ENV_TOOL_EXPOSURE = "DCC_MCP_MAYA_TOOL_EXPOSURE"
#: dcc-mcp-core#656 (0.14.22) — toggle the Cursor-safe tool-name format
#: (``i_<id8>__<escaped_tool>``) emitted by the upstream gateway.  The
#: default is ``True`` on the core side; set ``DCC_MCP_MAYA_CURSOR_SAFE_TOOL_NAMES=0``
#: to restore the legacy dotted ``<id8>.<tool>`` form during a migration
#: window.  Only consulted when a gateway port is configured.
ENV_CURSOR_SAFE_TOOL_NAMES = "DCC_MCP_MAYA_CURSOR_SAFE_TOOL_NAMES"
#: Issue #174 — when set to ``"1"``, ``__skill__*`` and ``__group__*``
#: stubs are removed from the registry after skill discovery, so that
#: the backend ``tools/list`` no longer exposes Progressive-loading
#: placeholders.  This is the *backend half* of the REST-backed redesign:
#: skill discovery moves to the capability catalog and ``/v1/search``,
#: keeping the MCP ``tools/list`` compact for token-constrained clients.
#:
#: Default: ``"0"`` (stubs are registered — backwards-compatible).
ENV_EXCLUDE_STUBS_FROM_TOOLS_LIST = "DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST"

#: Accepted values for :data:`ENV_TOOL_EXPOSURE`.  Kept as a module-level
#: tuple so the resolver and its unit tests share a single source of
#: truth.
VALID_TOOL_EXPOSURE_MODES = ("full", "slim", "both", "rest")

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


def resolve_enable_workflows(enable_workflows: Optional[bool] = None) -> bool:
    """Resolve whether to enable the upstream workflow engine.

    When ``True``, ``McpHttpConfig.enable_workflows`` is flipped so the
    upstream ``workflows.run`` / ``workflows.resume`` / ``workflows.list_runs``
    MCP tools (added by dcc-mcp-core#565) become reachable from
    ``tools/list``.  Off by default to keep the minimal-mode tools list
    tight (issue #139).

    Priority: explicit ``enable_workflows`` argument >
    ``DCC_MCP_MAYA_ENABLE_WORKFLOWS=1`` > ``False``.
    """
    if enable_workflows is not None:
        return bool(enable_workflows)
    return os.environ.get(ENV_ENABLE_WORKFLOWS, "").strip() == "1"


def resolve_tool_exposure(tool_exposure: Optional[str] = None) -> Optional[str]:
    """Resolve the gateway ``tools/list`` shaping mode (core 0.14.22).

    Returns one of the strings in :data:`VALID_TOOL_EXPOSURE_MODES`, or
    ``None`` when neither caller nor environment supplied a value (in
    which case callers should leave :attr:`McpHttpConfig.gateway_tool_exposure`
    at whatever default the current core exposes — today ``"full"``).

    Priority order:

    1. Explicit ``tool_exposure`` argument (when not ``None``).
    2. ``DCC_MCP_MAYA_TOOL_EXPOSURE`` env var.
    3. Unset → return ``None`` so the inner config's default is kept.

    Invalid values (typos, mixed-case beyond the canonical lowercase,
    empty strings) collapse to ``None`` and emit a debug log line so a
    Maya session never fails to start over a misconfigured env var.
    """
    raw: Optional[str]
    if tool_exposure is not None:
        raw = tool_exposure
    else:
        raw = os.environ.get(ENV_TOOL_EXPOSURE)
    if raw is None:
        return None
    normalised = str(raw).strip().lower()
    if not normalised:
        return None
    if normalised not in VALID_TOOL_EXPOSURE_MODES:
        logger.warning(
            "Ignoring invalid %s=%r (expected one of %s); falling back to inner default",
            ENV_TOOL_EXPOSURE,
            raw,
            VALID_TOOL_EXPOSURE_MODES,
        )
        return None
    return normalised


def resolve_cursor_safe_tool_names(cursor_safe: Optional[bool] = None) -> Optional[bool]:
    """Resolve the Cursor-safe tool-name toggle (core 0.14.22).

    Returns ``True`` / ``False`` to drive :attr:`McpHttpConfig.gateway_cursor_safe_tool_names`,
    or ``None`` when neither caller nor environment opted in (leaves the
    inner config's default — currently ``True`` on the core side).

    Priority order:

    1. Explicit ``cursor_safe`` argument (when not ``None``).
    2. ``DCC_MCP_MAYA_CURSOR_SAFE_TOOL_NAMES``:
       - ``"0"`` / ``"false"`` / ``"no"`` → ``False``
       - ``"1"`` / ``"true"`` / ``"yes"`` → ``True``
       - any other value → ``None`` with a debug log line so the inner
         default is preserved.
    3. Unset → ``None``.
    """
    if cursor_safe is not None:
        return bool(cursor_safe)
    raw = os.environ.get(ENV_CURSOR_SAFE_TOOL_NAMES)
    if raw is None:
        return None
    normalised = raw.strip().lower()
    if normalised in ("0", "false", "no", "off"):
        return False
    if normalised in ("1", "true", "yes", "on"):
        return True
    logger.debug(
        "Ignoring invalid %s=%r (expected 0/1/true/false); leaving inner default",
        ENV_CURSOR_SAFE_TOOL_NAMES,
        raw,
    )
    return None


# Backwards-compatibility aliases — the leading-underscore names mirror the
# previous module-private constants in ``server.py`` so any unit test or
# downstream patcher that reaches in still works.
_ENV_MINIMAL = ENV_MINIMAL
_ENV_DEFAULT_TOOLS = ENV_DEFAULT_TOOLS
_ENV_METRICS = ENV_METRICS
_ENV_JOB_STORAGE = ENV_JOB_STORAGE
_ENV_JOB_RECOVERY = ENV_JOB_RECOVERY
_DEFAULT_JOB_DB_FILENAME = DEFAULT_JOB_DB_FILENAME


def resolve_exclude_stubs_from_tools_list(exclude: Optional[bool] = None) -> bool:
    """Resolve whether to exclude ``__skill__*`` / ``__group__*`` stubs from ``tools/list``.

    When ``True``, :meth:`MayaMcpServer.register_builtin_actions`
    unregisters all ``__skill__<name>`` and ``__group__<name>`` entries
    from the registry after :meth:`discover` so that the backend MCP
    ``tools/list`` stays compact.  Discovery is still possible via the
    capability catalog (``build_capability_manifest``) and the REST
    ``/v1/search`` endpoint.

    This is the *backend half* of the REST-backed redesign (issue #174):
    the gateway already filters stubs on its side (core#677); this flag
    removes them at the source so that every connected MCP client benefits,
    not just the gateway.

    **Default:** ``False`` — stubs are registered (backwards-compatible).

    Priority order:

    1. Explicit ``exclude`` argument (when not ``None``).
    2. ``DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST`` env var:
       ``"0"`` / ``"false"`` / ``"no"`` / ``"off"`` → ``False``
       ``"1"`` / ``"true"`` / ``"yes"`` / ``"on"`` → ``True``
    3. Unset → ``False``.
    """
    if exclude is not None:
        return bool(exclude)
    raw = os.environ.get(ENV_EXCLUDE_STUBS_FROM_TOOLS_LIST)
    if raw is None:
        return False
    normalised = raw.strip().lower()
    if normalised in ("0", "false", "no", "off"):
        return False
    if normalised in ("1", "true", "yes", "on"):
        return True
    logger.debug(
        "Ignoring invalid %s=%r (expected 0/1/true/false); defaulting to False",
        ENV_EXCLUDE_STUBS_FROM_TOOLS_LIST,
        raw,
    )
    return False


def _unused_marker(_value: Any) -> None:  # pragma: no cover
    """Sentinel referencing :data:`Any` so the type-only import is retained."""
    return None
