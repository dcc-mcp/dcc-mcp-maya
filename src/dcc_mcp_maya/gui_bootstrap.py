"""Non-interactive Maya GUI bootstrap and bounded readiness diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

PathLike = Union[str, Path]

ENV_GUI_BOOTSTRAP_LOG = "DCC_MCP_MAYA_BOOTSTRAP_LOG"
PLUGIN_NAME = "dcc_mcp_maya_plugin"

_MAYA_GUI_BOOTSTRAP_PYTHON = (
    "import maya.cmds as cmds; "
    "cmds.evalDeferred(lambda: __import__('dcc_mcp_maya.gui_bootstrap', "
    "fromlist=['bootstrap_in_maya']).bootstrap_in_maya(), lowestPriority=True)"
)


def build_maya_launch_args(maya_executable: PathLike) -> List[str]:
    """Build the fixed non-interactive GUI bootstrap command."""
    mel_command = 'python("{}")'.format(_MAYA_GUI_BOOTSTRAP_PYTHON.replace("\\", "\\\\").replace('"', '\\"'))
    return [os.fspath(maya_executable), "-command", mel_command]


def _registry_directory(registry_base: Optional[PathLike] = None) -> Path:
    from dcc_mcp_maya._stale_cleanup import registry_path

    explicit_base = os.fspath(registry_base) if registry_base is not None else None
    return registry_path(explicit_base).resolve().parent


def launch_maya_gui(
    *,
    maya_executable: PathLike,
    timeout_secs: float = 120.0,
    registry_base: Optional[PathLike] = None,
    log_path: Optional[PathLike] = None,
) -> Dict[str, Any]:
    """Launch Maya with the fixed bootstrap and return one bounded diagnosis."""
    executable = Path(maya_executable).resolve()
    if not executable.is_file():
        raise FileNotFoundError("Maya executable not found: {}".format(executable))

    resolved_log_path = (
        Path(log_path).resolve()
        if log_path is not None
        else Path(tempfile.gettempdir()) / "dcc-mcp-maya" / "gui-bootstrap-{}.jsonl".format(uuid.uuid4().hex)
    )
    resolved_registry_base = (
        Path(registry_base).resolve()
        if registry_base is not None
        else Path(os.environ.get("DCC_MCP_REGISTRY_DIR") or tempfile.gettempdir()).resolve()
    )
    env = os.environ.copy()
    env[ENV_GUI_BOOTSTRAP_LOG] = os.fspath(resolved_log_path)
    env["DCC_MCP_REGISTRY_DIR"] = os.fspath(resolved_registry_base)
    process = subprocess.Popen(build_maya_launch_args(executable), env=env)
    result = probe_gui_readiness(
        log_path=resolved_log_path,
        registry_dir=_registry_directory(resolved_registry_base),
        maya_pid=process.pid,
        timeout_secs=timeout_secs,
    )
    result["maya_pid"] = process.pid
    result["bootstrap_log"] = os.fspath(resolved_log_path)
    return result


def record_bootstrap_stage(log_path: PathLike, stage: str, status: str, **details: Any) -> Dict[str, Any]:
    """Append one JSONL stage without touching Maya or the registry."""
    event = {
        "schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "stage": str(stage),
        "status": str(status),
    }
    event.update(details)
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def bootstrap_in_maya() -> None:
    """Resolve and load the packaged plug-in without changing its Auto Load state."""
    log_path = os.environ[ENV_GUI_BOOTSTRAP_LOG]
    prior_events = _read_bootstrap_stages(log_path)
    record_bootstrap_stage(log_path, "plugin_invoked", "started")
    record_bootstrap_stage(log_path, "plugin_resolution", "started", plugin_name=PLUGIN_NAME)

    plugin_filename = PLUGIN_NAME + ".py"
    plugin_path = next(
        (
            candidate.resolve()
            for directory in os.environ.get("MAYA_PLUG_IN_PATH", "").split(os.pathsep)
            if directory
            for candidate in [Path(directory) / plugin_filename]
            if candidate.is_file()
        ),
        None,
    )
    if plugin_path is None:
        record_bootstrap_stage(
            log_path,
            "plugin_resolution",
            "failed",
            plugin_name=PLUGIN_NAME,
            error_type="FileNotFoundError",
        )
        raise RuntimeError("The packaged dcc-mcp Maya plug-in was not found")
    record_bootstrap_stage(
        log_path,
        "plugin_resolution",
        "succeeded",
        plugin_name=PLUGIN_NAME,
        plugin_path=os.fspath(plugin_path),
    )

    from maya import cmds

    record_bootstrap_stage(log_path, "plugin_load", "started", plugin_name=PLUGIN_NAME)
    try:
        already_loaded = bool(cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True))
        if not already_loaded:
            cmds.loadPlugin(os.fspath(plugin_path), quiet=True)
    except Exception as exc:
        record_bootstrap_stage(
            log_path,
            "plugin_load",
            "failed",
            plugin_name=PLUGIN_NAME,
            error_type=type(exc).__name__,
        )
        raise
    record_bootstrap_stage(
        log_path,
        "plugin_load",
        "succeeded",
        plugin_name=PLUGIN_NAME,
        already_loaded=already_loaded,
    )
    if already_loaded:
        prior_failure = next((event for event in reversed(prior_events) if event.get("status") == "failed"), None)
        if prior_failure is not None:
            failure_details = {
                key: value
                for key, value in prior_failure.items()
                if key not in {"schema_version", "timestamp_utc", "pid", "stage", "status"}
            }
            record_bootstrap_stage(log_path, prior_failure["stage"], "failed", **failure_details)
        else:
            record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded", already_loaded=True)


def _read_bootstrap_stages(log_path: PathLike) -> List[Dict[str, Any]]:
    path = Path(log_path)
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("stage") and event.get("status"):
            events.append(event)
    return events


def _public_stage(event: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in event.items() if key not in {"schema_version", "timestamp_utc", "pid"}}


def _iter_registry_entries(payload: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(payload, list):
        for entry in payload:
            if isinstance(entry, dict):
                yield entry
        return
    if not isinstance(payload, dict):
        return
    services = payload.get("services", payload)
    values = services.values() if isinstance(services, dict) else services
    if not isinstance(values, (list, tuple)) and not hasattr(values, "__iter__"):
        return
    for entry in values:
        if isinstance(entry, dict):
            yield entry


def _matching_maya_entry(registry_dir: PathLike, maya_pid: int) -> Optional[Dict[str, Any]]:
    services_path = Path(registry_dir) / "services.json"
    if not services_path.is_file():
        return None
    try:
        payload = json.loads(services_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for entry in _iter_registry_entries(payload):
        metadata = entry.get("metadata") or {}
        dcc_type = entry.get("dcc_type") or metadata.get("dcc_type")
        host_pid = entry.get("host_pid") or metadata.get("host_pid")
        owner_pid = entry.get("pid")
        if dcc_type == "maya" and int(maya_pid) in {owner_pid, host_pid}:
            return entry
    return None


def _public_instance(entry: Dict[str, Any]) -> Dict[str, Any]:
    metadata = entry.get("metadata") or {}
    return {
        "instance_id": entry.get("instance_id") or entry.get("id"),
        "dcc_type": entry.get("dcc_type") or metadata.get("dcc_type"),
        "pid": entry.get("pid"),
        "host_pid": entry.get("host_pid") or metadata.get("host_pid"),
        "mcp_url": metadata.get("mcp_url") or entry.get("mcp_url"),
    }


def probe_gui_readiness(
    *,
    log_path: PathLike,
    registry_dir: PathLike,
    maya_pid: int,
    timeout_secs: float,
    poll_interval_secs: float = 0.1,
) -> Dict[str, Any]:
    """Return a bounded diagnosis for one non-interactive GUI launch."""
    deadline = time.monotonic() + max(0.0, float(timeout_secs))
    interval = max(0.001, float(poll_interval_secs))
    while True:
        result, terminal = _probe_gui_readiness_once(
            log_path=log_path,
            registry_dir=registry_dir,
            maya_pid=maya_pid,
        )
        if terminal or time.monotonic() >= deadline:
            return result
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))


def _probe_gui_readiness_once(
    *,
    log_path: PathLike,
    registry_dir: PathLike,
    maya_pid: int,
) -> tuple:
    stages = _read_bootstrap_stages(log_path)
    if not stages:
        return (
            {
                "ready": False,
                "failure_reason": "plugin_not_invoked",
                "last_stage": None,
                "next_action": {
                    "action": "retry_gui_launch",
                    "command": "python -m dcc_mcp_maya.gui_bootstrap launch",
                },
            },
            False,
        )
    last_stage = stages[-1]
    if last_stage["status"] == "failed" and last_stage["stage"] in {
        "plugin_resolution",
        "plugin_load",
        "adapter_import",
    }:
        return (
            {
                "ready": False,
                "failure_reason": "plugin_load_failed",
                "last_stage": _public_stage(last_stage),
                "next_action": {
                    "action": "inspect_bootstrap_log",
                    "stage": last_stage["stage"],
                },
            },
            True,
        )
    if last_stage["status"] == "failed" and last_stage["stage"] == "sidecar_spawn":
        return (
            {
                "ready": False,
                "failure_reason": "sidecar_failed",
                "last_stage": _public_stage(last_stage),
                "next_action": {
                    "action": "inspect_sidecar_logs",
                    "stage": "sidecar_spawn",
                },
            },
            True,
        )
    if last_stage["stage"] == "registry_registration":
        return (
            {
                "ready": False,
                "failure_reason": "registry_registration_failed",
                "last_stage": _public_stage(last_stage),
                "next_action": {
                    "action": "inspect_registry",
                    "dcc_type": "maya",
                    "maya_pid": int(maya_pid),
                },
            },
            last_stage["status"] == "failed",
        )
    instance_entry = _matching_maya_entry(registry_dir, maya_pid)
    if (
        instance_entry is not None
        and last_stage["stage"] == "bootstrap_complete"
        and last_stage["status"] == "succeeded"
    ):
        instance = _public_instance(instance_entry)
        return (
            {
                "ready": True,
                "failure_reason": None,
                "last_stage": _public_stage(last_stage),
                "instance": instance,
                "next_action": {
                    "action": "use_registered_instance",
                    "instance_id": instance["instance_id"],
                },
            },
            True,
        )
    if last_stage["stage"] == "bootstrap_complete" and last_stage["status"] == "succeeded":
        return (
            {
                "ready": False,
                "failure_reason": "registry_registration_failed",
                "last_stage": _public_stage(last_stage),
                "next_action": {
                    "action": "inspect_registry",
                    "dcc_type": "maya",
                    "maya_pid": int(maya_pid),
                },
            },
            False,
        )
    reason = "sidecar_failed" if last_stage["stage"] == "sidecar_spawn" else "plugin_load_failed"
    action = "inspect_sidecar_logs" if reason == "sidecar_failed" else "inspect_bootstrap_log"
    return (
        {
            "ready": False,
            "failure_reason": reason,
            "last_stage": _public_stage(last_stage),
            "next_action": {"action": action, "stage": last_stage["stage"]},
        },
        False,
    )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch or probe the fixed Maya GUI bootstrap")
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch_parser = subparsers.add_parser("launch", help="launch Maya GUI and wait for registration")
    launch_parser.add_argument("--maya-executable", required=True)
    launch_parser.add_argument("--timeout", type=float, default=120.0)
    launch_parser.add_argument("--registry-dir", dest="registry_base")
    launch_parser.add_argument("--log-path")

    probe_parser = subparsers.add_parser("probe", help="probe an already launched diagnostic bootstrap")
    probe_parser.add_argument("--maya-pid", type=int, required=True)
    probe_parser.add_argument("--log-path", required=True)
    probe_parser.add_argument("--timeout", type=float, default=120.0)
    probe_parser.add_argument("--registry-dir", dest="registry_base")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Run the machine-readable bootstrap diagnostic CLI."""
    args = _argument_parser().parse_args(argv)
    try:
        if args.command == "launch":
            result = launch_maya_gui(
                maya_executable=args.maya_executable,
                timeout_secs=args.timeout,
                registry_base=args.registry_base,
                log_path=args.log_path,
            )
        else:
            result = probe_gui_readiness(
                log_path=args.log_path,
                registry_dir=_registry_directory(args.registry_base),
                maya_pid=args.maya_pid,
                timeout_secs=args.timeout,
            )
            result["maya_pid"] = args.maya_pid
            result["bootstrap_log"] = os.fspath(Path(args.log_path).resolve())
    except (OSError, ValueError) as exc:
        payload = {
            "schema_version": 1,
            "ready": False,
            "failure_reason": "launch_failed",
            "error_type": type(exc).__name__,
            "next_action": {"action": "check_launch_arguments"},
        }
        print(json.dumps(payload, sort_keys=True))
        return 40

    payload = {"schema_version": 1}
    payload.update(result)
    print(json.dumps(payload, sort_keys=True))
    return 0 if result["ready"] else 10


if __name__ == "__main__":  # pragma: no cover - exercised through ``main``
    sys.exit(main())
