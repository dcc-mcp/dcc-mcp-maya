"""Bootstrap hang watchdog for the Maya ``userSetup`` auto-load path.

:mod:`maya.userSetup` reports *exceptions* through ``_report_failure``, but a
load that never returns raises nothing: ``cmds.loadPlugin`` can block forever
inside Maya's main thread and leave no trace at all. That is the one failure
mode an operator still cannot see from outside -- the process is alive, the
deferred queue has drained, and no receipt is ever written.

This module makes the *pending* state observable with two artefacts that live
beside the existing failure receipts in ``DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR``:

* ``pending/<run_id>.json`` -- one marker per in-flight bootstrap, carrying
  ``pid`` / ``stage`` / ``timestamp_utc`` / ``host``. It is written once per
  run before the first load is scheduled and removed as soon as the load
  finishes, or once the run stops trying. A marker that survives is a load
  that never returned.
* ``userSetup-<YYYYMMDD>.jsonl`` -- the append-only trail of *terminal*
  events (``finished`` / ``hang_detected``, alongside the existing
  ``failed`` records). One day of history stays one greppable file.

Detection is deliberately advisory: nothing here aborts, times out, or
otherwise changes the load semantics. It only answers the question "did the
previous start ever finish?".

Operator contract
-----------------
``started`` written, ``finished`` never written, and the marker is older than
the threshold => the bootstrap hung::

    from dcc_mcp_maya import detect_bootstrap_hang

    for hang in detect_bootstrap_hang():
        print(hang["age_secs"], hang["pid"], hang["marker_path"])

The threshold defaults to 60 seconds and is overridden with
``DCC_MCP_MAYA_BOOTSTRAP_TIMEOUT`` (seconds). A non-positive value disables
detection entirely.

Design (SOLID)
--------------
* **Single responsibility** -- this module records and judges bootstrap
  markers; it never loads the plug-in itself.
* **Dependency inversion** -- every path is injectable (``environ``,
  ``now``, ``timeout_secs``), so tests need no clock or filesystem tricks.
* **Fail-open** -- a watchdog that can break the boot it is watching is worse
  than no watchdog, so every write is best-effort.

This module is intentionally free of ``maya`` and ``dcc_mcp_core`` imports at
module scope: it must stay importable (and unit-testable) outside Maya, and it
must stay usable when the adapter package itself is the thing that is broken.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ENV_BOOTSTRAP_ERROR_DIR = "DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR"
ENV_BOOTSTRAP_TIMEOUT = "DCC_MCP_MAYA_BOOTSTRAP_TIMEOUT"

DEFAULT_BOOTSTRAP_TIMEOUT_SECS = 60.0

BOOTSTRAP_STAGE = "bootstrap_user_setup"
STATUS_STARTED = "started"
STATUS_FINISHED = "finished"
STATUS_HANG_DETECTED = "hang_detected"

PENDING_DIR_NAME = "pending"
BOOTSTRAP_LOG_PREFIX = "userSetup"
SCHEMA_VERSION = 1


def resolve_bootstrap_timeout_secs(environ: Optional[Dict[str, str]] = None) -> Optional[float]:
    """Return the hang threshold in seconds, or ``None`` when disabled.

    An unset, empty, or unparsable value falls back to
    :data:`DEFAULT_BOOTSTRAP_TIMEOUT_SECS`. A non-positive value disables
    detection -- that is the escape hatch for studios whose Maya cold start
    legitimately exceeds the default window.
    """
    source = os.environ if environ is None else environ
    raw = source.get(ENV_BOOTSTRAP_TIMEOUT)
    if raw is None:
        return DEFAULT_BOOTSTRAP_TIMEOUT_SECS
    raw = raw.strip()
    if not raw:
        return DEFAULT_BOOTSTRAP_TIMEOUT_SECS
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        logger.warning("%s=%r is not a number; using %.1fs", ENV_BOOTSTRAP_TIMEOUT, raw, DEFAULT_BOOTSTRAP_TIMEOUT_SECS)
        return DEFAULT_BOOTSTRAP_TIMEOUT_SECS
    if parsed <= 0:
        return None
    return parsed


def bootstrap_error_dir(environ: Optional[Dict[str, str]] = None) -> Path:
    """Return the directory that receives bootstrap receipts."""
    source = os.environ if environ is None else environ
    override = source.get(ENV_BOOTSTRAP_ERROR_DIR)
    if override:
        return Path(override)
    return Path.home() / ".dcc-mcp" / "receipts" / "bootstrap-errors"


def bootstrap_pending_dir(environ: Optional[Dict[str, str]] = None) -> Path:
    """Return the directory holding one marker per in-flight bootstrap."""
    return bootstrap_error_dir(environ) / PENDING_DIR_NAME


def bootstrap_log_path(now: Optional[datetime] = None, environ: Optional[Dict[str, str]] = None) -> Path:
    """Return the daily JSONL audit trail path (matches ``_report_failure``)."""
    moment = now or datetime.now(timezone.utc)
    return bootstrap_error_dir(environ) / "{}-{}.jsonl".format(BOOTSTRAP_LOG_PREFIX, moment.strftime("%Y%m%d"))


def _host_name() -> str:
    try:
        return socket.gethostname()
    except Exception:  # pragma: no cover - hostname lookup is best-effort
        return "unknown"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _append_record(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _marker_path(run_id: str, environ: Optional[Dict[str, str]] = None) -> Path:
    return bootstrap_pending_dir(environ) / "{}.json".format(run_id)


def record_bootstrap_started(
    stage: str = BOOTSTRAP_STAGE,
    environ: Optional[Dict[str, str]] = None,
    **details: Any,
) -> Dict[str, Any]:
    """Write the ``started`` marker and return it.

    The returned dict carries the ``run_id`` that
    :func:`record_bootstrap_finished` / :func:`clear_bootstrap_marker` need to
    retire the marker. Every write is best-effort: a watchdog that prevents the
    boot it is watching is worse than no watchdog.

    The marker is written *only* to ``pending/<run_id>.json``, never to the
    daily JSONL. That split is deliberate: the JSONL is the stream of
    terminal events (``failed`` / ``finished`` / ``hang_detected``) that
    operators and tests read to answer "what happened", while ``pending/``
    answers the different question "is something still in flight". Mixing an
    in-flight record into the terminal stream would also make it look like a
    load was attempted in runs that were only ever scheduled.
    """
    moment = _utc_now()
    timeout_secs = resolve_bootstrap_timeout_secs(environ)
    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": uuid.uuid4().hex,
        "stage": stage,
        "status": STATUS_STARTED,
        "timestamp_utc": moment.isoformat(),
        "timestamp_epoch": time.time(),
        "pid": os.getpid(),
        "host": _host_name(),
        "timeout_secs": timeout_secs,
        "hang_reported": False,
    }
    record.update(details)
    try:
        marker_path = _marker_path(record["run_id"], environ)
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        record["marker_path"] = str(marker_path)
    except Exception as exc:
        logger.warning("dcc-mcp-maya bootstrap marker could not be written: %s", exc)
        record["marker_path"] = None
    return record


def clear_bootstrap_marker(marker: Optional[Dict[str, Any]], environ: Optional[Dict[str, str]] = None) -> bool:
    """Remove the pending marker for ``marker``. Return ``True`` when removed.

    Used on the failure path: the exception receipt already explains what went
    wrong, so keeping a "still running" marker would later be misread as a hang.
    """
    run_id = (marker or {}).get("run_id")
    if not run_id:
        return False
    try:
        path = _marker_path(str(run_id), environ)
    except Exception:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True


def record_bootstrap_finished(
    marker: Optional[Dict[str, Any]],
    stage: Optional[str] = None,
    environ: Optional[Dict[str, str]] = None,
    **details: Any,
) -> Dict[str, Any]:
    """Write the ``finished`` receipt and retire the pending marker."""
    moment = _utc_now()
    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": (marker or {}).get("run_id"),
        "stage": stage or (marker or {}).get("stage") or BOOTSTRAP_STAGE,
        "status": STATUS_FINISHED,
        "timestamp_utc": moment.isoformat(),
        "timestamp_epoch": time.time(),
        "pid": os.getpid(),
        "host": _host_name(),
        "hang_reported": False,
    }
    if marker:
        record["started_utc"] = marker.get("timestamp_utc")
    record.update(details)
    try:
        _append_record(bootstrap_log_path(moment, environ), record)
    except Exception as exc:
        logger.warning("dcc-mcp-maya bootstrap log could not be written: %s", exc)
    clear_bootstrap_marker(marker, environ)
    return record


def read_pending_markers(
    pending_dir: Optional[Path] = None,
    environ: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Return every marker currently sitting in the pending directory."""
    directory = Path(pending_dir) if pending_dir is not None else bootstrap_pending_dir(environ)
    markers: List[Dict[str, Any]] = []
    if not directory.is_dir():
        return markers
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        payload.setdefault("run_id", path.stem)
        payload["marker_path"] = str(path)
        payload["marker_mtime"] = path.stat().st_mtime
        markers.append(payload)
    return markers


def read_bootstrap_records(
    log_dir: Optional[Path] = None, environ: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """Return the JSONL audit records for ``log_dir`` (newest file last)."""
    directory = Path(log_dir) if log_dir is not None else bootstrap_error_dir(environ)
    records: List[Dict[str, Any]] = []
    if not directory.is_dir():
        return records
    for path in sorted(directory.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _marker_age_secs(marker: Dict[str, Any], path: Path, now: float) -> float:
    started = marker.get("timestamp_epoch")
    if isinstance(started, (int, float)) and not isinstance(started, bool):
        return max(0.0, now - float(started))
    try:
        return max(0.0, now - path.stat().st_mtime)
    except OSError:
        return 0.0


def detect_bootstrap_hang(
    pending_dir: Optional[Path] = None,
    environ: Optional[Dict[str, str]] = None,
    timeout_secs: Optional[float] = None,
    now: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Return one report per bootstrap that started and never finished.

    A marker is judged *hung* when its age exceeds the threshold. Detection
    returns ``[]`` when the threshold is disabled (``<= 0``), when no marker
    exists, or when every marker has been retired by a finished load.
    """
    threshold = resolve_bootstrap_timeout_secs(environ) if timeout_secs is None else timeout_secs
    if threshold is None or threshold <= 0:
        return []
    moment = time.time() if now is None else now
    error_dir = bootstrap_error_dir(environ)
    reports: List[Dict[str, Any]] = []
    for marker in read_pending_markers(pending_dir, environ):
        path = Path(marker.get("marker_path") or _marker_path(str(marker.get("run_id")), environ))
        age = _marker_age_secs(marker, path, moment)
        if age <= threshold:
            continue
        report = {
            "hang": True,
            "run_id": marker.get("run_id"),
            "stage": marker.get("stage") or BOOTSTRAP_STAGE,
            "status": STATUS_HANG_DETECTED,
            "pid": marker.get("pid"),
            "host": marker.get("host"),
            "started_utc": marker.get("timestamp_utc"),
            "age_secs": round(age, 3),
            "threshold_secs": threshold,
            "hang_reported": bool(marker.get("hang_reported")),
            "marker_path": str(path),
            "evidence_log": str(error_dir),
            "next_action": "inspect_bootstrap_hang",
        }
        reports.append(report)
    return reports


def _warn(message: str) -> None:
    """Mirror a warning onto Maya's Script Editor, then the logging module."""
    try:
        import maya.cmds as cmds

        cmds.warning(message)
    except Exception:
        pass
    logger.warning("%s", message)


def _hang_message(report: Dict[str, Any]) -> str:
    return (
        "dcc-mcp-maya bootstrap hang detected ({stage}): the load started {age:.1f}s ago "
        "(threshold {threshold:.1f}s) and never returned (pid={pid} host={host} run={run_id}). "
        "The plug-in load is blocked, not failed -- check the Maya main thread. "
        "Evidence: {evidence}; delete {marker} to clear this warning."
    ).format(
        stage=report.get("stage"),
        age=float(report.get("age_secs") or 0.0),
        threshold=float(report.get("threshold_secs") or 0.0),
        pid=report.get("pid"),
        host=report.get("host"),
        run_id=report.get("run_id"),
        evidence=report.get("evidence_log"),
        marker=report.get("marker_path"),
    )


def report_bootstrap_hang(
    pending_dir: Optional[Path] = None,
    environ: Optional[Dict[str, str]] = None,
    timeout_secs: Optional[float] = None,
    now: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Surface every hung bootstrap on the next start-up.

    Each newly found hang is written to the JSONL audit trail *and* pushed
    through :func:`_warn`, so the evidence is retrievable even when the Script
    Editor history has scrolled away. Markers already reported are returned but
    not re-announced, which keeps a permanently wedged Maya from flooding the
    log on every launch.
    """
    reports = detect_bootstrap_hang(
        pending_dir=pending_dir,
        environ=environ,
        timeout_secs=timeout_secs,
        now=now,
    )
    if not reports:
        return reports
    moment = _utc_now()
    for report in reports:
        report["reported"] = False
        if report.get("hang_reported"):
            continue
        _warn(_hang_message(report))
        try:
            _append_record(bootstrap_log_path(moment, environ), report)
        except Exception as exc:
            logger.warning("dcc-mcp-maya bootstrap log could not be written: %s", exc)
        _mark_reported(report, environ)
        report["reported"] = True
        report["hang_reported"] = True
    return reports


def _mark_reported(report: Dict[str, Any], environ: Optional[Dict[str, str]] = None) -> None:
    """Flip ``hang_reported`` on the marker file so it is announced once."""
    marker_path = report.get("marker_path")
    if not marker_path:
        return
    path = Path(marker_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        return
    payload["hang_reported"] = True
    payload["hang_reported_utc"] = _utc_now().isoformat()
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        logger.warning("dcc-mcp-maya bootstrap marker could not be updated: %s", exc)
