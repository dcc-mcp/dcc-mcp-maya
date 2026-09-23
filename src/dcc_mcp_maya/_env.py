"""Environment-variable resolution for ``MayaMcpServer`` (issue #127).

Centralises every ``DCC_MCP_MAYA_*`` env var used by the server so the
composition root in :mod:`dcc_mcp_maya.server` stays a thin orchestrator.

All helpers are pure functions: they read :data:`os.environ` and return
plain Python values; they never mutate global state.

See: https://github.com/dcc-mcp/dcc-mcp-maya/issues/127
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Public env-var names ─────────────────────────────────────────────────────
#: TCP port for this Maya's MCP HTTP server.  ``0`` asks the OS for a free
#: port; read only when the caller leaves ``port=None``.
ENV_PORT = "DCC_MCP_MAYA_PORT"
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
#: When set, overrides the ``enable_gateway_failover`` constructor flag so
#: integration tests and operators can force failover on/off without code
#: changes (matches ``tests/fixtures/maya_instances.py``).
ENV_ENABLE_GATEWAY_FAILOVER = "DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER"
#: When ``"1"`` / ``"true"`` / ``"yes"``, :func:`execute_python` returns a
#: structured refusal so agents must use ``load_skill`` + typed tools.
ENV_DISABLE_EXECUTE_PYTHON = "DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON"
#: When set (same truthy tokens as above), both ``execute_python`` and
#: ``execute_mel`` are refused — strictest pipeline / classroom mode.
ENV_DISABLE_ARBITRARY_SCRIPT = "DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT"
#: Optional per-tool opt-out for MEL when arbitrary script is otherwise allowed.
ENV_DISABLE_EXECUTE_MEL = "DCC_MCP_MAYA_DISABLE_EXECUTE_MEL"
#: Issue #174 / #238 — omit ``__skill__*`` / ``__group__*`` from ``tools/list``.
#: Applied by core ``DccServerBase`` (``dcc-mcp-core>=0.17.3``); discovery via
#: ``search_tools``, capability manifest, or gateway ``/v1/search``.
ENV_EXCLUDE_STUBS_FROM_TOOLS_LIST = "DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST"
#: Env var that disables project-tools registration.  ``"0"`` → disabled,
#: anything else (including unset) → enabled.
ENV_PROJECT_TOOLS = "DCC_MCP_MAYA_PROJECT_TOOLS"

#: Default SQLite filename inside the platform data directory.
DEFAULT_JOB_DB_FILENAME = "jobs.db"

#: Fallback MCP HTTP port when neither the caller nor ``DCC_MCP_MAYA_PORT``
#: supplies one.  ``0`` lets the OS pick a free port.
DEFAULT_PORT = 0
#: Inclusive TCP port bounds accepted by :func:`resolve_port`.
MIN_PORT = 0
MAX_PORT = 65535


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def resolve_execute_python_disabled() -> bool:
    """Return True when ``execute_python`` must refuse all calls.

    ``DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT`` implies this flag.  Used by
    ``maya-scripting`` scripts so studios can enforce skills-first workflows.
    """
    if _env_truthy(ENV_DISABLE_ARBITRARY_SCRIPT):
        return True
    return _env_truthy(ENV_DISABLE_EXECUTE_PYTHON)


def resolve_execute_mel_disabled() -> bool:
    """Return True when ``execute_mel`` must refuse all calls."""
    if _env_truthy(ENV_DISABLE_ARBITRARY_SCRIPT):
        return True
    return _env_truthy(ENV_DISABLE_EXECUTE_MEL)


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


def _coerce_port(value: object, source: str) -> int:
    """Return ``value`` as a validated TCP port, or raise a readable error.

    Raises:
        ValueError: if ``value`` is not an integer in ``[0, 65535]``.  The
            message names the offending source so callers never have to read
            a Rust ``TypeError`` to find out a port was malformed.
    """
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source} must be an integer between {MIN_PORT} and {MAX_PORT}, got {value!r}") from exc
    if not MIN_PORT <= parsed <= MAX_PORT:
        raise ValueError(f"{source} must be an integer between {MIN_PORT} and {MAX_PORT}, got {value!r}")
    return parsed


def resolve_port(port: Optional[int] = None, *, default: int = DEFAULT_PORT) -> int:
    """Resolve the MCP HTTP instance port to a concrete integer.

    ``None`` means "caller did not specify" — the adapter then falls back to
    ``DCC_MCP_MAYA_PORT`` and finally to :data:`DEFAULT_PORT` (``0``, i.e. an
    OS-assigned free port).  :meth:`MayaServerOptions.to_core_options`
    resolves here so a concrete ``int`` always reaches
    ``DccServerOptions.from_env``.

    .. note::

       **This is a legacy-core compatibility shim.**
       ``dcc-mcp-core>=0.19.45`` already performs the identical resolution
       inside ``DccServerOptions.from_env`` — same ``DCC_MCP_MAYA_PORT``
       name, same ``0`` fallback, same ``[0, 65535]`` bounds, and it already
       raises a readable ``ValueError``.  On those releases the shim is
       behaviour-neutral: it moves the computation one layer up and never
       lets ``None`` cross the adapter boundary.

       It exists because cores older than 0.19.45 — including the 0.19.2
       build the original crash was reported against — forward ``None``
       straight into the Rust ``McpHttpConfig`` constructor::

           TypeError: argument 'port': 'NoneType' object cannot be
           interpreted as an integer

       Removal condition: raise the ``dcc-mcp-core`` floor in
       ``pyproject.toml`` to ``>=0.19.45`` *and* confirm no shipped Maya
       environment still resolves an older core.  Until then keep the shim
       so ``start_server()`` works regardless of which core the host has.

    Priority: explicit ``port`` argument > ``DCC_MCP_MAYA_PORT`` (when set and
    non-empty) > ``default``.  A blank ``DCC_MCP_MAYA_PORT`` is treated as
    unset; core would reject it with ``ValueError`` instead.

    Raises:
        ValueError: if the resolved value is outside ``[0, 65535]``.
    """
    if port is not None:
        return _coerce_port(port, "port")
    raw = os.environ.get(ENV_PORT, "").strip()
    if not raw:
        return _coerce_port(default, "port default")
    return _coerce_port(raw, ENV_PORT)


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


def resolve_enable_gateway_failover(
    enable_gateway_failover: Optional[bool],
    *,
    default: bool = True,
) -> bool:
    """Resolve gateway failover from constructor + optional env override.

    Priority: explicit ``enable_gateway_failover`` argument (when not ``None``)
    > ``DCC_MCP_MAYA_ENABLE_GATEWAY_FAILOVER`` (when set) > ``default``.

    This matches :func:`resolve_metrics_enabled` and avoids CI subprocess env
    accidentally defeating ``MayaMcpServer(..., enable_gateway_failover=False)``.
    """
    if enable_gateway_failover is not None:
        return bool(enable_gateway_failover)
    raw = os.environ.get(ENV_ENABLE_GATEWAY_FAILOVER, "").strip()
    if raw:
        return _env_truthy(ENV_ENABLE_GATEWAY_FAILOVER)
    return bool(default)


def resolve_project_tools_enabled(flag: bool | None = None) -> bool:
    """Resolve whether project tools should be wired in.

    Priority: explicit ``flag`` argument > ``DCC_MCP_MAYA_PROJECT_TOOLS``
    env var (``"0"`` disables) > ``True``.
    """
    if flag is not None:
        return bool(flag)
    raw = os.environ.get(ENV_PROJECT_TOOLS)
    if raw is None:
        return True
    return raw.strip() != "0"
