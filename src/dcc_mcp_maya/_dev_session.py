"""Development-session helpers for MCP-assisted Maya tool authoring.

The ``maya-dev`` skill exposes these helpers as typed tools.  Keeping the
state in a package module (rather than in individual skill scripts) makes the
session survive core's per-call script loading model.
"""

from __future__ import annotations

import base64
import contextlib
import difflib
import importlib
import io
import json
import os
import runpy
import socket
import sys
import tempfile
import threading
import time
import traceback
import weakref
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from dcc_mcp_core.adapter_contracts import (
    DebugPathMapping,
    DebugSessionDescriptor,
    DebugSessionStatus,
    UiActionKind,
    UiActionResult,
    UiArtifactRef,
    UiBounds,
    UiControlNode,
    UiErrorCode,
    UiSnapshot,
)
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

ENV_DEV_ROOTS = "DCC_MCP_MAYA_DEV_ROOTS"
ENV_DEBUGPY_LOG_DIR = "DCC_MCP_MAYA_DEBUGPY_LOG_DIR"
ENV_DEV_ARTIFACT_DIR = "DCC_MCP_MAYA_DEV_ARTIFACT_DIR"
DEFAULT_ARTIFACT_THRESHOLD = 4096
DEFAULT_SESSION_EVENT_INSTANCE_ID = "maya-dev"

_LOCK = threading.RLock()
_DEBUGPY_STATE: Dict[str, Any] = {
    "listening": False,
    "host": None,
    "port": None,
    "log_dir": None,
    "python_executable": None,
    "path_mappings": [],
}
_UI_STATE: Dict[str, Any] = {
    "session_id": "maya-ui-1",
    "refs": {},
    "seq": 0,
}
_SESSION_EVENT_STATE: Dict[str, Any] = {
    "buffer": None,
    "instance_id": None,
    "resource_uri": None,
    "registered": False,
}


@dataclass
class DevProject:
    """A project root attached to the live Maya Python session."""

    name: str
    root: str
    package_prefixes: Tuple[str, ...] = ()
    sys_path_entries: Tuple[str, ...] = ()
    attached_at: float = field(default_factory=time.time)

    def to_context(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "root": self.root,
            "package_prefixes": list(self.package_prefixes),
            "sys_path_entries": list(self.sys_path_entries),
            "attached_at": self.attached_at,
        }


_STATE: Dict[str, Any] = {
    "active": None,
    "projects": {},
}


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.replace("\n", ",")
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(path))))


def _display_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _split_env_paths(raw: str) -> List[str]:
    if not raw:
        return []
    paths: List[str] = []
    for part in raw.split(os.pathsep):
        part = part.strip().strip('"')
        if part:
            paths.append(part)
    return paths


def _is_under(child: str, parent: str) -> bool:
    try:
        return os.path.commonpath([_norm(child), _norm(parent)]) == _norm(parent)
    except (OSError, ValueError):
        return False


def _allowed_roots() -> List[str]:
    return [_display_path(path) for path in _split_env_paths(os.environ.get(ENV_DEV_ROOTS, ""))]


def _validate_allowed_root(root: str) -> Optional[Dict[str, Any]]:
    roots = _allowed_roots()
    if not roots:
        return None
    if any(_is_under(root, allowed) for allowed in roots):
        return None
    return skill_error(
        "Project root is outside allowed development roots",
        "{} is set; attach a project below one of those roots.".format(ENV_DEV_ROOTS),
        possible_solutions=[
            "Choose a project under an allowed development root.",
            "Update {} before starting Maya if this root should be trusted.".format(ENV_DEV_ROOTS),
        ],
        env_var=ENV_DEV_ROOTS,
        allowed_root_count=len(roots),
    )


def _normalize_prefixes(prefixes: Any) -> Tuple[str, ...]:
    cleaned: List[str] = []
    for raw in _as_list(prefixes):
        value = raw.strip()
        if not value:
            continue
        # Dotted package prefixes only.  A bad prefix is more likely to purge
        # too much than to help, so silently ignore obviously invalid values.
        parts = value.split(".")
        if all(part.isidentifier() for part in parts):
            cleaned.append(value)
    return tuple(dict.fromkeys(cleaned))


def _project_name_from_root(root: str) -> str:
    name = os.path.basename(os.path.normpath(root)) or "maya-dev-project"
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name)


def _get_project(project_name: Optional[str] = None) -> Tuple[Optional[DevProject], Optional[Dict[str, Any]]]:
    with _LOCK:
        name = project_name or _STATE.get("active")
        projects = _STATE.get("projects") or {}
        if not name:
            return None, skill_error(
                "No development project is attached",
                "Call maya_dev__attach_project before running project code.",
                possible_solutions=["Attach a project root first."],
            )
        project = projects.get(name)
        if project is None:
            return None, skill_error(
                "Development project not found",
                "No attached project named {!r}.".format(name),
                attached_projects=sorted(projects.keys()),
            )
        return project, None


def _prepend_sys_path(entries: Iterable[str]) -> List[str]:
    added: List[str] = []
    for entry in reversed([_display_path(e) for e in entries if e]):
        if entry not in sys.path:
            sys.path.insert(0, entry)
            added.append(entry)
    added.reverse()
    return added


def attach_project(
    project_root: str,
    name: Optional[str] = None,
    package_prefixes: Any = None,
    include_src: bool = True,
    make_active: bool = True,
) -> Dict[str, Any]:
    """Attach a Python tool project to the live Maya session."""

    if not project_root:
        return skill_error("No project root provided", "Pass project_root as an absolute path.")

    root = _display_path(project_root)
    if not os.path.isdir(root):
        return skill_error(
            "Project root not found",
            "The supplied project_root does not exist or is not a directory.",
            project_root=root,
        )

    denied = _validate_allowed_root(root)
    if denied is not None:
        return denied

    sys_path_entries = [root]
    src_root = os.path.join(root, "src")
    if include_src and os.path.isdir(src_root):
        sys_path_entries.append(src_root)

    added = _prepend_sys_path(sys_path_entries)
    project_name = str(name or _project_name_from_root(root)).strip() or _project_name_from_root(root)
    prefixes = _normalize_prefixes(package_prefixes)
    project = DevProject(
        name=project_name,
        root=root,
        package_prefixes=prefixes,
        sys_path_entries=tuple(sys_path_entries),
    )

    with _LOCK:
        _STATE["projects"][project_name] = project
        if make_active:
            _STATE["active"] = project_name

    return skill_success(
        "Development project attached: {}".format(project_name),
        prompt="Use reload_modules then run_entrypoint or run_check to execute project code inside Maya.",
        project=project.to_context(),
        active_project=_STATE.get("active"),
        added_sys_path=added,
        reused_sys_path=[entry for entry in sys_path_entries if entry not in added],
    )


def _module_file(module: Any) -> Optional[str]:
    path = getattr(module, "__file__", None)
    if not path:
        return None
    try:
        return _display_path(path)
    except Exception:
        return None


def _matches_module(name: str, module: Any, project: DevProject, prefixes: Tuple[str, ...]) -> bool:
    if name == "__main__" or name.startswith("_maya_skill_script"):
        return False

    module_path = _module_file(module)
    under_root = bool(module_path and _is_under(module_path, project.root))
    if prefixes:
        prefix_match = any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)
        return bool(prefix_match and (under_root or module_path is None))
    return under_root


def _bounded(items: Sequence[str], limit: int = 200) -> Tuple[List[str], int]:
    shown = list(items[:limit])
    return shown, max(0, len(items) - len(shown))


def reload_modules(
    project_name: Optional[str] = None,
    package_prefixes: Any = None,
    mode: str = "purge",
) -> Dict[str, Any]:
    """Reload or purge modules that belong to an attached project."""

    project, error = _get_project(project_name)
    if error is not None:
        return error
    assert project is not None

    mode = (mode or "purge").strip().lower()
    if mode not in {"purge", "reload"}:
        return skill_error("Invalid reload mode", "mode must be 'purge' or 'reload'.", mode=mode)

    prefixes = _normalize_prefixes(package_prefixes) or project.package_prefixes
    matches = [name for name, module in list(sys.modules.items()) if _matches_module(name, module, project, prefixes)]
    matches = sorted(set(matches), key=lambda item: (item.count("."), item))
    errors: List[Dict[str, str]] = []
    changed: List[str] = []

    if mode == "purge":
        for name in sorted(matches, key=lambda item: (item.count("."), item), reverse=True):
            sys.modules.pop(name, None)
            changed.append(name)
    else:
        for name in matches:
            module = sys.modules.get(name)
            if module is None:
                continue
            try:
                importlib.reload(module)
                changed.append(name)
            except Exception as exc:  # noqa: BLE001
                errors.append({"module": name, "error": repr(exc)})

    shown, omitted = _bounded(changed)
    return skill_success(
        "Project modules {}ed: {}".format(mode, len(changed)),
        project=project.to_context(),
        mode=mode,
        package_prefixes=list(prefixes),
        module_count=len(changed),
        modules=shown,
        omitted_module_count=omitted,
        errors=errors,
    )


def _parse_target(target: Optional[str], module: Optional[str], callable_name: Optional[str]) -> Tuple[str, str]:
    if target:
        raw = str(target).strip()
        if ":" in raw:
            mod_name, attr = raw.split(":", 1)
            return mod_name.strip(), attr.strip() or "main"
        return raw, str(callable_name or "main").strip()
    return str(module or "").strip(), str(callable_name or "main").strip()


def _resolve_callable(module_name: str, callable_name: str) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
    if not module_name:
        return None, skill_error(
            "No module provided", "Pass target='package.module:function' or module='package.module'."
        )
    if not callable_name:
        callable_name = "main"
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        return None, skill_exception(exc, message="Failed to import module {}".format(module_name))

    obj: Any = module
    for part in callable_name.split("."):
        if not part:
            continue
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None, skill_error(
                "Callable not found",
                "{} has no attribute path {!r}.".format(module_name, callable_name),
                module=module_name,
                callable=callable_name,
            )
    if not callable(obj):
        return None, skill_error(
            "Resolved object is not callable",
            "{}:{} is not callable.".format(module_name, callable_name),
            module=module_name,
            callable=callable_name,
        )
    return obj, None


def _jsonable(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


def _result_context(value: Any) -> Dict[str, Any]:
    ctx = {
        "return_type": type(value).__name__,
        "return_repr": repr(value),
    }
    if _jsonable(value):
        ctx["return_value"] = value
    return ctx


@contextlib.contextmanager
def _maybe_chdir(path: Optional[str]):
    if not path:
        yield
        return
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _run_callable(
    fn: Any,
    args: Any = None,
    kwargs: Any = None,
    capture_output: bool = True,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    call_args = args if isinstance(args, (list, tuple)) else []
    call_kwargs = kwargs if isinstance(kwargs, dict) else {}
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    started = time.time()
    try:
        with _maybe_chdir(cwd):
            if capture_output:
                with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                    value = fn(*call_args, **call_kwargs)
            else:
                value = fn(*call_args, **call_kwargs)
        elapsed = time.time() - started
        ctx = _result_context(value)
        ctx.update(
            {
                "stdout": stdout_buf.getvalue() if capture_output else "",
                "stderr": stderr_buf.getvalue() if capture_output else "",
                "elapsed_secs": elapsed,
            }
        )
        return skill_success("Entrypoint executed", **ctx)
    except Exception as exc:  # noqa: BLE001
        elapsed = time.time() - started
        return skill_error(
            "Entrypoint execution failed",
            repr(exc),
            traceback=traceback.format_exc(),
            stdout=stdout_buf.getvalue() if capture_output else "",
            stderr=stderr_buf.getvalue() if capture_output else "",
            elapsed_secs=elapsed,
        )


def run_entrypoint(
    target: Optional[str] = None,
    module: Optional[str] = None,
    callable: Optional[str] = None,  # noqa: A002 - public tool parameter
    args: Any = None,
    kwargs: Any = None,
    project_name: Optional[str] = None,
    reload_before: bool = True,
    reload_mode: str = "purge",
    capture_output: bool = True,
    chdir_project: bool = True,
) -> Dict[str, Any]:
    """Run a Python callable from an attached project inside Maya."""

    project, error = _get_project(project_name)
    if error is not None:
        return error
    assert project is not None

    reload_context: Optional[Dict[str, Any]] = None
    if reload_before:
        reload_result = reload_modules(project.name, mode=reload_mode)
        reload_context = reload_result.get("context", reload_result)

    module_name, callable_name = _parse_target(target, module, callable)
    fn, resolve_error = _resolve_callable(module_name, callable_name)
    if resolve_error is not None:
        if reload_context is not None:
            resolve_error.setdefault("context", {})["reload"] = reload_context
        return resolve_error
    assert fn is not None

    result = _run_callable(
        fn,
        args=args,
        kwargs=kwargs,
        capture_output=bool(capture_output),
        cwd=project.root if chdir_project else None,
    )
    ctx = result.setdefault("context", {})
    ctx.update(
        {
            "project": project.to_context(),
            "target": "{}:{}".format(module_name, callable_name),
        }
    )
    if reload_context is not None:
        ctx["reload"] = reload_context
    return result


def _resolve_script_path(script_path: str, project: DevProject) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    if not script_path:
        return None, skill_error(
            "No script path provided", "Pass script_path as a project-relative or absolute .py path."
        )
    path = script_path
    if not os.path.isabs(path):
        path = os.path.join(project.root, path)
    path = _display_path(path)
    if not os.path.isfile(path):
        return None, skill_error("Script not found", "The supplied script_path does not exist.", script_path=path)
    if not path.lower().endswith(".py"):
        return None, skill_error("Unsupported script type", "Only .py scripts are supported.", script_path=path)
    if not _is_under(path, project.root):
        return None, skill_error(
            "Script is outside the attached project",
            "run_script only executes files below the attached development root.",
            script_path=path,
            project_root=project.root,
        )
    return path, None


def run_script(
    script_path: str,
    argv: Any = None,
    project_name: Optional[str] = None,
    reload_before: bool = True,
    reload_mode: str = "purge",
    capture_output: bool = True,
    chdir_project: bool = True,
) -> Dict[str, Any]:
    """Run a Python script file below the attached project root."""

    project, error = _get_project(project_name)
    if error is not None:
        return error
    assert project is not None

    resolved, path_error = _resolve_script_path(script_path, project)
    if path_error is not None:
        return path_error
    assert resolved is not None

    reload_context: Optional[Dict[str, Any]] = None
    if reload_before:
        reload_result = reload_modules(project.name, mode=reload_mode)
        reload_context = reload_result.get("context", reload_result)

    script_argv = _as_list(argv)
    old_argv = sys.argv[:]
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    started = time.time()
    try:
        sys.argv = [resolved] + script_argv
        with _maybe_chdir(project.root if chdir_project else None):
            if capture_output:
                with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                    globals_after = runpy.run_path(resolved, run_name="__main__")
            else:
                globals_after = runpy.run_path(resolved, run_name="__main__")
        elapsed = time.time() - started
        ctx = {
            "project": project.to_context(),
            "script_path": resolved,
            "argv": script_argv,
            "stdout": stdout_buf.getvalue() if capture_output else "",
            "stderr": stderr_buf.getvalue() if capture_output else "",
            "elapsed_secs": elapsed,
            "global_names": sorted(k for k in globals_after if not k.startswith("__"))[:200],
        }
        if reload_context is not None:
            ctx["reload"] = reload_context
        return skill_success("Script executed", **ctx)
    except Exception as exc:  # noqa: BLE001
        elapsed = time.time() - started
        return skill_error(
            "Script execution failed",
            repr(exc),
            traceback=traceback.format_exc(),
            stdout=stdout_buf.getvalue() if capture_output else "",
            stderr=stderr_buf.getvalue() if capture_output else "",
            elapsed_secs=elapsed,
            script_path=resolved,
            project=project.to_context(),
            reload=reload_context,
        )
    finally:
        sys.argv = old_argv


def _path_uri(path: str) -> str:
    return "file:///" + os.path.abspath(path).replace("\\", "/").lstrip("/")


def _artifact_dir() -> str:
    raw = os.environ.get(ENV_DEV_ARTIFACT_DIR, "").strip()
    root = raw or os.path.join(tempfile.gettempdir(), "dcc-mcp-maya-dev-artifacts")
    root = _display_path(root)
    os.makedirs(root, exist_ok=True)
    return root


def _artifact_path(kind: str, suffix: str) -> Tuple[str, str]:
    safe_kind = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in kind) or "text"
    filename = "{}-{}-{}{}".format(int(time.time() * 1000), threading.get_ident(), safe_kind, suffix)
    path = os.path.join(_artifact_dir(), filename)
    return safe_kind, path


def _artifact_payload(kind: str, path: str, mime: str, byte_count: int) -> Dict[str, Any]:
    ref = UiArtifactRef(uri=_path_uri(path), mime=mime).to_dict()
    ref.update(
        {
            "kind": kind,
            "path": path,
            "bytes": int(byte_count),
        }
    )
    return ref


def _write_text_artifact(kind: str, text: str) -> Dict[str, Any]:
    safe_kind, path = _artifact_path(kind, ".txt")
    with open(path, "w", encoding="utf-8", errors="replace") as fh:
        fh.write(text)
    return _artifact_payload(safe_kind, path, "text/plain", len(text.encode("utf-8", errors="replace")))


def _create_session_event_buffer(instance_id: str) -> Optional[Any]:
    """Create core's bounded runtime-event buffer when the API exists."""
    try:
        from dcc_mcp_core import SessionEventBuffer  # noqa: PLC0415
    except Exception:
        return None
    try:
        return SessionEventBuffer(instance_id)
    except Exception:
        return None


def _get_or_create_session_event_buffer(instance_id: Optional[str] = None) -> Optional[Any]:
    with _LOCK:
        existing = _SESSION_EVENT_STATE.get("buffer")
        if instance_id is None and existing is not None:
            return existing
        resolved = str(instance_id or _SESSION_EVENT_STATE.get("instance_id") or DEFAULT_SESSION_EVENT_INSTANCE_ID)
        if existing is not None and _SESSION_EVENT_STATE.get("instance_id") == resolved:
            return existing
        buffer = _create_session_event_buffer(resolved)
        _SESSION_EVENT_STATE.update(
            {
                "buffer": buffer,
                "instance_id": resolved if buffer is not None else None,
                "resource_uri": getattr(buffer, "resource_uri", None) if buffer is not None else None,
                "registered": False,
            }
        )
        return buffer


def get_session_event_buffer(instance_id: Optional[str] = None) -> Optional[Any]:
    """Return the maya-dev runtime-event buffer, if supported by installed core."""
    return _get_or_create_session_event_buffer(instance_id)


def register_session_event_buffer(resources_handle: Any, instance_id: Optional[str] = None) -> Dict[str, Any]:
    """Register maya-dev's session event buffer as ``events://session/*``.

    This is intentionally best-effort so older core builds keep the inline
    result behavior that ``maya-dev`` had before runtime event buffers existed.
    """
    buffer = _get_or_create_session_event_buffer(instance_id)
    if buffer is None:
        return _session_event_context(published_count=0)
    register = getattr(resources_handle, "register_session_event_buffer", None)
    if not callable(register):
        return _session_event_context(published_count=0)
    try:
        register(buffer)
    except Exception:
        return _session_event_context(published_count=0)
    with _LOCK:
        _SESSION_EVENT_STATE["registered"] = True
        _SESSION_EVENT_STATE["resource_uri"] = getattr(buffer, "resource_uri", None)
    return _session_event_context(published_count=0)


def _session_event_context(published_count: int) -> Dict[str, Any]:
    with _LOCK:
        buffer = _SESSION_EVENT_STATE.get("buffer")
        return {
            "available": buffer is not None,
            "registered": bool(_SESSION_EVENT_STATE.get("registered")),
            "instance_id": _SESSION_EVENT_STATE.get("instance_id"),
            "resource_uri": _SESSION_EVENT_STATE.get("resource_uri"),
            "published_count": int(published_count),
        }


def _append_session_event(
    stream: str,
    message: str,
    *,
    level: str = "info",
    session_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    job_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    buffer = _get_or_create_session_event_buffer()
    if buffer is None or not message:
        return None
    try:
        return buffer.append(
            source="maya-dev",
            stream=stream,
            message=message,
            level=level,
            session_id=session_id,
            tool_call_id=tool_call_id,
            job_id=job_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
    except Exception:
        return None


def _publish_run_check_events(
    run_context: Dict[str, Any],
    run_summary: Dict[str, Any],
    artifacts: Sequence[Dict[str, Any]],
    *,
    run_success: bool,
    session_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    job_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    artifacts_by_kind = {str(artifact.get("kind")): artifact for artifact in artifacts if artifact.get("kind")}
    base_metadata = {
        "target": run_summary.get("target"),
        "elapsed_secs": run_summary.get("elapsed_secs"),
        "run_success": bool(run_success),
    }
    common = {
        "session_id": session_id,
        "tool_call_id": tool_call_id,
        "job_id": job_id,
        "correlation_id": correlation_id,
    }

    published = 0
    progress = _append_session_event(
        "progress",
        "run_check {} for {}".format(
            "completed" if run_success else "failed", run_summary.get("target") or "entrypoint"
        ),
        level="info" if run_success else "error",
        metadata=dict(base_metadata, run_summary=run_summary),
        **common,
    )
    if progress is not None:
        published += 1

    for stream, level in (("stdout", "info"), ("stderr", "warning"), ("traceback", "error")):
        text = run_context.get(stream)
        if not isinstance(text, str) or not text:
            continue
        metadata = dict(base_metadata, char_count=len(text))
        artifact = artifacts_by_kind.get(stream)
        if artifact:
            metadata["artifact"] = {
                "uri": artifact.get("uri"),
                "mime": artifact.get("mime"),
                "bytes": artifact.get("bytes"),
            }
        event = _append_session_event(stream, text, level=level, metadata=metadata, **common)
        if event is not None:
            published += 1

    return _session_event_context(published)


def _ui_artifact_refs(artifacts: Sequence[Dict[str, Any]]) -> List[UiArtifactRef]:
    refs: List[UiArtifactRef] = []
    for artifact in artifacts:
        uri = artifact.get("uri")
        if uri:
            refs.append(UiArtifactRef(uri=str(uri), mime=artifact.get("mime")))
    return refs


def _externalize_text_fields(ctx: Dict[str, Any], fields: Sequence[str], threshold: int) -> List[Dict[str, Any]]:
    if threshold <= 0:
        threshold = 1
    artifacts: List[Dict[str, Any]] = []
    for field_name in fields:
        value = ctx.get(field_name)
        if isinstance(value, str) and value and len(value) >= threshold:
            artifacts.append(_write_text_artifact(field_name, value))
    return artifacts


def _runtime_name() -> str:
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        version = cmds.about(version=True)
        return "Maya {}".format(version)
    except Exception:
        return "Python {}".format(sys.version.split()[0])


def _resolve_debug_python(python_executable: Optional[str], configure_python: bool) -> Optional[str]:
    if not configure_python:
        return None
    raw = python_executable or sys.executable
    if not raw:
        return None
    try:
        from dcc_mcp_core import correct_python_executable, is_gui_executable  # noqa: PLC0415

        if is_gui_executable(raw):
            fixed = correct_python_executable(raw)
            if fixed:
                return str(fixed)
    except Exception:
        pass
    return _display_path(raw)


def _normalize_path_mappings(value: Any = None) -> List[DebugPathMapping]:
    mappings: List[DebugPathMapping] = []
    raw_items = value if isinstance(value, list) else []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        local = item.get("local_root") or item.get("localRoot") or item.get("local")
        remote = item.get("remote_root") or item.get("remoteRoot") or item.get("remote")
        if local and remote:
            mappings.append(DebugPathMapping(local_root=_display_path(str(local)), remote_root=str(remote)))

    with _LOCK:
        project_names = [_STATE.get("active")] + sorted((_STATE.get("projects") or {}).keys())
        seen = {(m.local_root, m.remote_root) for m in mappings}
        for name in project_names:
            if not name:
                continue
            project = (_STATE.get("projects") or {}).get(name)
            if project is None:
                continue
            pair = (project.root, project.root)
            if pair not in seen:
                mappings.append(DebugPathMapping(local_root=project.root, remote_root=project.root))
                seen.add(pair)
    return mappings


def _debug_descriptor(
    host: Optional[str],
    port: Optional[int],
    connected: bool,
    log_dir: Optional[str],
    python_executable: Optional[str],
    path_mappings: List[DebugPathMapping],
    status: Optional[str] = None,
    setup_instructions: Optional[str] = None,
) -> Dict[str, Any]:
    if status is None:
        status = DebugSessionStatus.CLIENT_CONNECTED if connected else DebugSessionStatus.LISTENING
    descriptor = DebugSessionDescriptor(
        debugger_kind="debugpy",
        status=status,
        host=host,
        port=port,
        runtime=_runtime_name(),
        process_id=os.getpid(),
        path_mappings=path_mappings,
        log_uri=_path_uri(log_dir) if log_dir else None,
        setup_instructions=setup_instructions,
        metadata={
            "python_executable": python_executable,
            "client_connected": connected,
        },
    )
    return descriptor.to_dict()


def _debugpy_status(message: str = "debugpy status", reused: bool = False) -> Dict[str, Any]:
    try:
        import debugpy  # noqa: PLC0415

        connected = bool(getattr(debugpy, "is_client_connected", lambda: False)())
    except ImportError:
        connected = False
    with _LOCK:
        path_mappings = list(_DEBUGPY_STATE.get("path_mappings") or [])
        host = _DEBUGPY_STATE.get("host")
        port = _DEBUGPY_STATE.get("port")
        log_dir = _DEBUGPY_STATE.get("log_dir")
        python_executable = _DEBUGPY_STATE.get("python_executable")
        listening = bool(_DEBUGPY_STATE.get("listening"))
    return skill_success(
        message,
        listening=listening,
        host=host,
        port=port,
        client_connected=connected,
        reused=bool(reused),
        path_mappings=[m.to_dict() for m in path_mappings],
        debug_session=_debug_descriptor(
            host=host,
            port=port,
            connected=connected,
            log_dir=log_dir,
            python_executable=python_executable,
            path_mappings=path_mappings,
            status=DebugSessionStatus.CLIENT_CONNECTED if connected else DebugSessionStatus.LISTENING,
        ),
    )


def _debugpy_error(
    message: str,
    error: str,
    error_code: str,
    possible_solutions: Optional[List[str]] = None,
    **context: Any,
) -> Dict[str, Any]:
    descriptor = DebugSessionDescriptor.unavailable("debugpy", error).to_dict()
    return skill_error(
        message,
        error,
        possible_solutions=possible_solutions,
        error_code=error_code,
        debug_session=descriptor,
        **context,
    )


def _port_is_busy(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def start_debugpy(
    host: str = "127.0.0.1",
    port: int = 5678,
    wait_for_client: bool = False,
    configure_python: bool = True,
    python_executable: Optional[str] = None,
    log_dir: Optional[str] = None,
    path_mappings: Any = None,
) -> Dict[str, Any]:
    """Start debugpy in the Maya process so an IDE can attach."""

    host = str(host or "127.0.0.1")
    port = int(port or 5678)
    with _LOCK:
        if _DEBUGPY_STATE.get("listening"):
            return _debugpy_status("debugpy is already listening", reused=True)

    try:
        import debugpy  # noqa: PLC0415
    except ImportError:
        return _debugpy_error(
            "debugpy is not installed; install it to unlock IDE attach debugging for this Maya session",
            "debugpy is optional, but enables stronger breakpoint debugging from Cursor or VS Code.",
            "debugpy_missing",
            possible_solutions=[
                "Run mayapy -m pip install debugpy for the Maya version you are debugging.",
                "Restart Maya after installing debugpy, then call start_debugpy again.",
            ],
        )

    debug_log_dir = (
        _display_path(log_dir or os.environ.get(ENV_DEBUGPY_LOG_DIR, "").strip())
        if (log_dir or os.environ.get(ENV_DEBUGPY_LOG_DIR, "").strip())
        else None
    )
    debug_python = _resolve_debug_python(python_executable, bool(configure_python))
    mappings = _normalize_path_mappings(path_mappings)
    try:
        if debug_log_dir:
            os.makedirs(debug_log_dir, exist_ok=True)
            log_to = getattr(debugpy, "log_to", None)
            if callable(log_to):
                log_to(debug_log_dir)
        if debug_python:
            configure = getattr(debugpy, "configure", None)
            if callable(configure):
                configure(python=debug_python)
        debugpy.listen((host, port))
        if wait_for_client:
            debugpy.wait_for_client()
        connected = bool(getattr(debugpy, "is_client_connected", lambda: False)())
    except RuntimeError as exc:
        message = str(exc).lower()
        if "address already" in message or "in use" in message or "10048" in message or _port_is_busy(host, port):
            return _debugpy_error(
                "debugpy port is already in use",
                str(exc),
                "port_in_use",
                possible_solutions=["Choose a different port or stop the process currently using it."],
                host=host,
                port=port,
            )
        if "already" in message:
            return _debugpy_error(
                "debugpy is already listening",
                str(exc),
                "debugger_already_listening",
                host=host,
                port=port,
            )
        return _debugpy_error(
            "Failed to start debugpy",
            str(exc),
            "debugpy_start_failed",
            host=host,
            port=port,
        )
    except OSError as exc:
        if _port_is_busy(host, port):
            return _debugpy_error(
                "debugpy port is already in use",
                str(exc),
                "port_in_use",
                possible_solutions=["Choose a different port or stop the process currently using it."],
                host=host,
                port=port,
            )
        return skill_exception(exc, message="Failed to start debugpy")
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to start debugpy")

    with _LOCK:
        _DEBUGPY_STATE.update(
            {
                "listening": True,
                "host": host,
                "port": port,
                "log_dir": debug_log_dir,
                "python_executable": debug_python,
                "path_mappings": mappings,
            }
        )

    return skill_success(
        "debugpy listening on {}:{}".format(host, port),
        listening=True,
        host=host,
        port=port,
        client_connected=connected,
        wait_for_client=bool(wait_for_client),
        configured_python_executable=debug_python,
        log_dir=debug_log_dir,
        log_uri=_path_uri(debug_log_dir) if debug_log_dir else None,
        path_mappings=[m.to_dict() for m in mappings],
        debug_session=_debug_descriptor(
            host=host,
            port=port,
            connected=connected,
            log_dir=debug_log_dir,
            python_executable=debug_python,
            path_mappings=mappings,
        ),
    )


def _qt_modules() -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[str]]:
    candidates = (
        ("PySide6", "shiboken6"),
        ("PySide2", "shiboken2"),
        ("PySide", "shiboken"),
    )
    for qt_name, shiboken_name in candidates:
        try:
            qt_widgets = importlib.import_module(qt_name + ".QtWidgets")
            qt_core = importlib.import_module(qt_name + ".QtCore")
            shiboken = importlib.import_module(shiboken_name)
            return qt_widgets, qt_core, shiboken, qt_name
        except ImportError:
            continue
    return None, None, None, None


def _maya_main_window() -> Tuple[Optional[Any], Optional[Any], Optional[Dict[str, Any]]]:
    qt_widgets, _qt_core, shiboken, qt_name = _qt_modules()
    if qt_widgets is None or shiboken is None:
        return (
            None,
            None,
            skill_error(
                "Qt bindings are not available",
                "Maya UI capture requires PySide/PySide2/PySide6 and shiboken.",
            ),
        )
    try:
        import maya.OpenMayaUI as omui  # noqa: PLC0415

        ptr = omui.MQtUtil.mainWindow()
    except Exception as exc:  # noqa: BLE001
        return None, None, skill_exception(exc, message="Failed to resolve Maya main window")
    if not ptr:
        return None, None, skill_error("Maya main window is unavailable", "UI capture only works in Maya GUI mode.")
    try:
        widget = shiboken.wrapInstance(int(ptr), qt_widgets.QWidget)
    except Exception as exc:  # noqa: BLE001
        return None, None, skill_exception(exc, message="Failed to wrap Maya main window ({})".format(qt_name))
    return widget, qt_widgets.QWidget, None


def _find_widget(root: Any, widget_type: Any, object_name: Optional[str]) -> Any:
    if not object_name:
        return root
    if str(root.objectName()) == object_name:
        return root
    found = root.findChild(widget_type, object_name)
    if found is not None:
        return found
    for child in root.findChildren(widget_type):
        try:
            if str(child.objectName()) == object_name or str(child.windowTitle()) == object_name:
                return child
        except Exception:
            continue
    return None


def _widget_text(widget: Any) -> Optional[str]:
    for name in ("text", "windowTitle", "title", "placeholderText", "accessibleName"):
        attr = getattr(widget, name, None)
        if not callable(attr):
            continue
        try:
            value = attr()
        except Exception:
            continue
        if value is not None and str(value):
            return str(value)
    return None


def _widget_tooltip(widget: Any) -> Optional[str]:
    attr = getattr(widget, "toolTip", None)
    if callable(attr):
        try:
            value = attr()
            return str(value) if value else None
        except Exception:
            return None
    return None


def _widget_object_name(widget: Any) -> Optional[str]:
    attr = getattr(widget, "objectName", None)
    if callable(attr):
        try:
            value = attr()
            return str(value) if value else None
        except Exception:
            return None
    return None


def _widget_visible(widget: Any) -> bool:
    attr = getattr(widget, "isVisible", None)
    if callable(attr):
        try:
            return bool(attr())
        except Exception:
            return True
    return True


def _widget_enabled(widget: Any) -> bool:
    attr = getattr(widget, "isEnabled", None)
    if callable(attr):
        try:
            return bool(attr())
        except Exception:
            return True
    return True


def _widget_checked(widget: Any) -> Optional[bool]:
    attr = getattr(widget, "isChecked", None)
    if callable(attr):
        try:
            return bool(attr())
        except Exception:
            return None
    return None


def _widget_value(widget: Any) -> Optional[str]:
    for name in ("currentText", "value", "plainText", "toPlainText"):
        attr = getattr(widget, name, None)
        if callable(attr):
            try:
                value = attr()
            except Exception:
                continue
            if value is not None and str(value):
                return str(value)
    return None


def _widget_bounds(widget: Any) -> Optional[UiBounds]:
    rect = None
    for name in ("geometry", "rect"):
        attr = getattr(widget, name, None)
        if callable(attr):
            try:
                rect = attr()
                break
            except Exception:
                continue
    if rect is None:
        return None

    def _num(obj: Any, attr_name: str) -> float:
        attr = getattr(obj, attr_name, None)
        if callable(attr):
            return float(attr())
        if attr is not None:
            return float(attr)
        return 0.0

    return UiBounds(
        x=_num(rect, "x"),
        y=_num(rect, "y"),
        width=_num(rect, "width"),
        height=_num(rect, "height"),
    )


def _widget_role(widget: Any) -> str:
    name = type(widget).__name__.lower()
    if "pushbutton" in name or name.endswith("button"):
        return "button"
    if "lineedit" in name or "textedit" in name or "plaintextedit" in name:
        return "textbox"
    if "checkbox" in name:
        return "checkbox"
    if "radiobutton" in name:
        return "radio"
    if "combobox" in name:
        return "combobox"
    if "label" in name:
        return "label"
    if "menu" in name:
        return "menu"
    is_window = getattr(widget, "isWindow", None)
    if callable(is_window):
        try:
            if is_window():
                return "window"
        except Exception:
            pass
    return "widget"


def _widget_children(widget: Any, widget_type: Any) -> List[Any]:
    raw: List[Any] = []
    children = getattr(widget, "children", None)
    if callable(children):
        try:
            raw = list(children())
        except Exception:
            raw = []
    elif hasattr(widget, "_children"):
        raw = list(getattr(widget, "_children"))
    if widget_type is None:
        return raw
    return [child for child in raw if isinstance(child, widget_type)]


def _widget_find_all(root: Any, widget_type: Any, include_root: bool = True) -> List[Any]:
    found = [root] if include_root else []
    find_children = getattr(root, "findChildren", None)
    if callable(find_children) and widget_type is not None:
        try:
            for child in find_children(widget_type):
                if child not in found:
                    found.append(child)
            return found
        except Exception:
            pass
    stack = list(_widget_children(root, widget_type))
    while stack:
        child = stack.pop(0)
        if child not in found:
            found.append(child)
            stack.extend(_widget_children(child, widget_type))
    return found


def _store_ui_ref(widget: Any) -> str:
    with _LOCK:
        _UI_STATE["seq"] = int(_UI_STATE.get("seq") or 0) + 1
        seq = int(_UI_STATE["seq"])
        object_name = _widget_object_name(widget)
        ref_id = "{}:{}:{}".format(_UI_STATE["session_id"], object_name or type(widget).__name__, seq)
        try:
            stored = weakref.ref(widget)
        except TypeError:

            def stored(widget=widget):
                return widget

        _UI_STATE.setdefault("refs", {})[ref_id] = stored
        return ref_id


def _resolve_ui_ref(control_id: str) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
    with _LOCK:
        stored = (_UI_STATE.get("refs") or {}).get(control_id)
    if stored is None:
        return None, skill_error(
            "UI control not found",
            "No control with id {!r}; call ui_snapshot or ui_find again.".format(control_id),
            error_code=UiErrorCode.NOT_FOUND,
            control_id=control_id,
        )
    widget = stored()
    if widget is None:
        return None, skill_error(
            "UI control is stale",
            "The referenced Qt widget no longer exists; refresh the UI snapshot.",
            error_code=UiErrorCode.STALE_CONTROL,
            action_result=UiActionResult.stale(control_id).to_dict(),
            control_id=control_id,
        )
    try:
        _qt_widgets, _qt_core, shiboken, _qt_name = _qt_modules()
        is_valid = getattr(shiboken, "isValid", None) if shiboken is not None else None
        if callable(is_valid) and not is_valid(widget):
            return None, skill_error(
                "UI control is stale",
                "The referenced Qt widget has been deleted; refresh the UI snapshot.",
                error_code=UiErrorCode.STALE_CONTROL,
                action_result=UiActionResult.stale(control_id).to_dict(),
                control_id=control_id,
            )
    except Exception:
        pass
    return widget, None


def _ui_ref(widget: Any, control_id: Optional[str] = None) -> Dict[str, Any]:
    ref_id = control_id or _store_ui_ref(widget)
    bounds = _widget_bounds(widget)
    return {
        "id": ref_id,
        "object_name": _widget_object_name(widget),
        "class": type(widget).__name__,
        "role": _widget_role(widget),
        "label": _widget_text(widget),
        "text": _widget_text(widget),
        "tooltip": _widget_tooltip(widget),
        "visible": _widget_visible(widget),
        "enabled": _widget_enabled(widget),
        "bounds": bounds.to_dict() if bounds else None,
        "value": _widget_value(widget),
        "checked": _widget_checked(widget),
        "stale": False,
    }


def _ui_node(
    widget: Any,
    widget_type: Any,
    max_depth: int,
    max_nodes: int,
    include_invisible: bool,
) -> Tuple[UiControlNode, int, bool]:
    count = 1
    truncated = False
    ref_id = _store_ui_ref(widget)
    bounds = _widget_bounds(widget)
    node = UiControlNode(
        id=ref_id,
        role=_widget_role(widget),
        label=_widget_text(widget),
        text=_widget_text(widget),
        object_name=_widget_object_name(widget),
        tooltip=_widget_tooltip(widget),
        enabled=_widget_enabled(widget),
        visible=_widget_visible(widget),
        bounds=bounds,
        value=_widget_value(widget),
        checked=_widget_checked(widget),
        metadata={"class": type(widget).__name__},
    )
    if max_depth <= 0 or count >= max_nodes:
        return node, count, bool(max_depth <= 0)

    for child in _widget_children(widget, widget_type):
        if not include_invisible and not _widget_visible(child):
            continue
        if count >= max_nodes:
            truncated = True
            break
        child_node, child_count, child_truncated = _ui_node(
            child,
            widget_type=widget_type,
            max_depth=max_depth - 1,
            max_nodes=max_nodes - count,
            include_invisible=include_invisible,
        )
        node.children.append(child_node)
        count += child_count
        truncated = truncated or child_truncated
    return node, count, truncated


def ui_snapshot(
    object_name: Optional[str] = None,
    max_depth: int = 4,
    max_nodes: int = 200,
    include_invisible: bool = False,
) -> Dict[str, Any]:
    """Return a bounded normalized Qt widget tree."""

    root, widget_type, error = _maya_main_window()
    if error is not None:
        return error
    assert root is not None
    assert widget_type is not None

    widget = _find_widget(root, widget_type, object_name)
    if widget is None:
        return skill_error(
            "Qt widget not found",
            "No Maya widget matched object_name={!r}.".format(object_name),
            error_code=UiErrorCode.NOT_FOUND,
            object_name=object_name,
        )
    max_depth = max(0, int(max_depth))
    max_nodes = max(1, int(max_nodes))
    root_node, node_count, truncated = _ui_node(widget, widget_type, max_depth, max_nodes, bool(include_invisible))
    with _LOCK:
        session_id = str(_UI_STATE["session_id"])
    snapshot = UiSnapshot(
        root=root_node,
        session_id=session_id,
        truncated=truncated,
        node_count=node_count,
        metadata={
            "object_name": object_name,
            "max_depth": max_depth,
            "max_nodes": max_nodes,
        },
    )
    return skill_success(
        "Maya UI snapshot captured",
        snapshot=snapshot.to_dict(),
        node_count=node_count,
        truncated=truncated,
    )


def _matches_text(actual: Optional[str], expected: Optional[str], fuzzy: bool) -> bool:
    if not expected:
        return True
    if actual is None:
        return False
    actual_l = actual.lower()
    expected_l = str(expected).lower()
    if expected_l in actual_l:
        return True
    if not fuzzy:
        return False
    return difflib.SequenceMatcher(None, actual_l, expected_l).ratio() >= 0.72


def _match_widget(
    widget: Any,
    query: Optional[str],
    object_name: Optional[str],
    role: Optional[str],
    label: Optional[str],
    text: Optional[str],
    window_title: Optional[str],
    tooltip: Optional[str],
    fuzzy: bool,
) -> bool:
    if object_name and _widget_object_name(widget) != object_name:
        return False
    if role and _widget_role(widget) != str(role).lower():
        return False
    if label and not _matches_text(_widget_text(widget), label, fuzzy):
        return False
    if text and not _matches_text(_widget_text(widget), text, fuzzy):
        return False
    if window_title:
        title_attr = getattr(widget, "windowTitle", None)
        try:
            title_value = title_attr() if callable(title_attr) else None
        except Exception:
            title_value = None
        if not _matches_text(str(title_value) if title_value else None, window_title, fuzzy):
            return False
    if tooltip and not _matches_text(_widget_tooltip(widget), tooltip, fuzzy):
        return False
    if query:
        haystack = " ".join(
            part
            for part in (
                _widget_object_name(widget),
                _widget_text(widget),
                _widget_tooltip(widget),
                type(widget).__name__,
                _widget_role(widget),
            )
            if part
        )
        if not _matches_text(haystack, query, fuzzy):
            return False
    return True


def ui_find(
    query: Optional[str] = None,
    object_name: Optional[str] = None,
    role: Optional[str] = None,
    label: Optional[str] = None,
    text: Optional[str] = None,
    window_title: Optional[str] = None,
    tooltip: Optional[str] = None,
    limit: int = 20,
    include_invisible: bool = False,
    fuzzy: bool = True,
) -> Dict[str, Any]:
    """Find Qt widgets by semantic locators."""

    if not any([query, object_name, role, label, text, window_title, tooltip]):
        return skill_error(
            "No UI locator provided",
            "Pass at least one of query, object_name, role, label, text, window_title, or tooltip.",
        )
    root, widget_type, error = _maya_main_window()
    if error is not None:
        return error
    assert root is not None
    assert widget_type is not None

    limit = max(1, int(limit or 20))
    matches: List[Dict[str, Any]] = []
    for widget in _widget_find_all(root, widget_type):
        if not include_invisible and not _widget_visible(widget):
            continue
        if _match_widget(widget, query, object_name, role, label, text, window_title, tooltip, bool(fuzzy)):
            matches.append(_ui_ref(widget))

    shown = matches[:limit]
    omitted = max(0, len(matches) - len(shown))
    message = "Found {} matching UI control(s)".format(len(matches))
    return skill_success(
        message,
        matches=shown,
        match_count=len(matches),
        omitted_match_count=omitted,
        truncated=omitted > 0,
    )


def _focus_id() -> Optional[str]:
    try:
        qt_widgets, _qt_core, _shiboken, _qt_name = _qt_modules()
        app = getattr(qt_widgets, "QApplication", None)
        focus_widget = app.focusWidget() if app is not None and callable(getattr(app, "focusWidget", None)) else None
        if focus_widget is not None:
            return _store_ui_ref(focus_widget)
    except Exception:
        return None
    return None


def _select_one_widget(
    control_id: Optional[str],
    query: Optional[str],
    object_name: Optional[str],
    role: Optional[str],
    label: Optional[str],
    text: Optional[str],
    window_title: Optional[str],
    tooltip: Optional[str],
) -> Tuple[Optional[Any], Optional[str], Optional[Dict[str, Any]]]:
    if control_id:
        widget, error = _resolve_ui_ref(control_id)
        return widget, control_id, error
    found = ui_find(
        query=query,
        object_name=object_name,
        role=role,
        label=label,
        text=text,
        window_title=window_title,
        tooltip=tooltip,
        limit=2,
    )
    if not found.get("success"):
        return None, None, found
    matches = found.get("context", {}).get("matches", [])
    if not matches:
        return (
            None,
            None,
            skill_error(
                "UI control not found",
                "No control matched the supplied locator.",
                error_code=UiErrorCode.NOT_FOUND,
            ),
        )
    if len(matches) > 1 or found.get("context", {}).get("match_count", 0) > 1:
        return (
            None,
            None,
            skill_error(
                "UI locator is ambiguous",
                "The supplied locator matched more than one control; pass control_id from ui_find.",
                error_code="ambiguous_control",
                matches=matches,
            ),
        )
    ref = matches[0]
    widget, error = _resolve_ui_ref(ref["id"])
    return widget, ref["id"], error


def _invoke_widget_action(
    widget: Any, action: str, text_value: Optional[str], checked: Optional[bool], option: Optional[str]
) -> None:
    action = (action or "").strip().lower()
    if action == UiActionKind.CLICK:
        click = getattr(widget, "click", None)
        if callable(click):
            click()
            return
        raise RuntimeError("Widget does not expose click()")
    if action == UiActionKind.FOCUS:
        focus = getattr(widget, "setFocus", None)
        if callable(focus):
            focus()
            return
        raise RuntimeError("Widget does not expose setFocus()")
    if action == UiActionKind.SET_TEXT:
        value = "" if text_value is None else str(text_value)
        for name in ("setText", "setPlainText"):
            setter = getattr(widget, name, None)
            if callable(setter):
                setter(value)
                return
        raise RuntimeError("Widget does not expose a text setter")
    if action == UiActionKind.TOGGLE:
        toggle = getattr(widget, "toggle", None)
        if callable(toggle):
            toggle()
            return
        click = getattr(widget, "click", None)
        if callable(click):
            click()
            return
        raise RuntimeError("Widget does not expose toggle() or click()")
    if action == UiActionKind.SET_CHECKED:
        setter = getattr(widget, "setChecked", None)
        if callable(setter):
            setter(bool(checked))
            return
        raise RuntimeError("Widget does not expose setChecked()")
    if action == UiActionKind.SELECT_OPTION:
        target = "" if option is None else str(option)
        find_text = getattr(widget, "findText", None)
        set_index = getattr(widget, "setCurrentIndex", None)
        set_current_text = getattr(widget, "setCurrentText", None)
        current_text = getattr(widget, "currentText", None)
        if callable(find_text):
            index = find_text(target)
            if index < 0:
                raise RuntimeError("Option {!r} not found".format(target))
            if callable(set_index):
                set_index(index)
            elif callable(set_current_text):
                set_current_text(target)
            else:
                raise RuntimeError("Widget does not expose combo-box selection APIs")
            if callable(current_text) and str(current_text()) != target:
                raise RuntimeError("Option {!r} was not selected".format(target))
            return
        if callable(set_current_text):
            set_current_text(target)
            if callable(current_text) and str(current_text()) != target:
                raise RuntimeError("Option {!r} was not selected".format(target))
            return
        raise RuntimeError("Widget does not expose combo-box selection APIs")
    raise RuntimeError("Unsupported UI action {!r}".format(action))


def _capture_widget_png_artifact(widget: Any, kind: str) -> Optional[Dict[str, Any]]:
    grab = getattr(widget, "grab", None)
    if not callable(grab):
        return None
    pixmap = grab()
    is_null = getattr(pixmap, "isNull", None)
    if callable(is_null) and is_null():
        return None

    safe_kind, path = _artifact_path(kind, ".png")
    save = getattr(pixmap, "save", None)
    if not callable(save) or not save(path, "PNG"):
        _remove_artifact_file(path)
        return None
    try:
        byte_count = os.path.getsize(path)
    except OSError:
        byte_count = 0
    if byte_count <= 0:
        _remove_artifact_file(path)
        return None
    return _artifact_payload(safe_kind, path, "image/png", byte_count)


def _remove_artifact_file(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def ui_action(
    action: str,
    control_id: Optional[str] = None,
    query: Optional[str] = None,
    object_name: Optional[str] = None,
    role: Optional[str] = None,
    label: Optional[str] = None,
    text: Optional[str] = None,
    window_title: Optional[str] = None,
    tooltip: Optional[str] = None,
    value: Optional[str] = None,
    checked: Optional[bool] = None,
    option: Optional[str] = None,
    capture_screenshots: bool = False,
) -> Dict[str, Any]:
    """Perform a bounded action on a unique Qt control."""

    normalized_action = (action or "").strip().lower()
    text_is_set_value = normalized_action == UiActionKind.SET_TEXT and value is None and text is not None
    locator_text = None if text_is_set_value else text
    action_text_value = value if value is not None else text if normalized_action == UiActionKind.SET_TEXT else None

    widget, resolved_id, error = _select_one_widget(
        control_id,
        query,
        object_name,
        role,
        label,
        locator_text,
        window_title,
        tooltip,
    )
    if error is not None:
        return error
    assert widget is not None
    assert resolved_id is not None

    if not _widget_visible(widget):
        return skill_error(
            "UI control is not visible",
            "The matched control is hidden; refresh the snapshot or choose another locator.",
            error_code="not_visible",
            control=_ui_ref(widget, resolved_id),
        )
    if not _widget_enabled(widget):
        return skill_error(
            "UI control is disabled",
            "The matched control is disabled and cannot be acted on.",
            error_code="disabled",
            control=_ui_ref(widget, resolved_id),
        )

    before_focus = _focus_id()
    before = _ui_ref(widget, resolved_id)
    artifacts: List[Dict[str, Any]] = []
    if capture_screenshots:
        before_artifact = _capture_widget_png_artifact(widget, "ui-action-before")
        if before_artifact is not None:
            artifacts.append(before_artifact)
    try:
        _invoke_widget_action(widget, normalized_action, action_text_value, checked, option)
    except Exception as exc:  # noqa: BLE001
        if capture_screenshots:
            after_artifact = _capture_widget_png_artifact(widget, "ui-action-after-error")
            if after_artifact is not None:
                artifacts.append(after_artifact)
        result = UiActionResult(
            success=False,
            control_id=resolved_id,
            error_code=UiErrorCode.UNSUPPORTED_ACTION,
            message=str(exc),
            before_focus_id=before_focus,
            artifacts=_ui_artifact_refs(artifacts),
        )
        return skill_error(
            "UI action failed",
            str(exc),
            error_code=result.error_code,
            action_result=result.to_dict(),
            control=before,
            artifacts=artifacts,
        )
    after_focus = _focus_id()
    after = _ui_ref(widget, resolved_id)
    if capture_screenshots:
        after_artifact = _capture_widget_png_artifact(widget, "ui-action-after")
        if after_artifact is not None:
            artifacts.append(after_artifact)
    result = UiActionResult(
        success=True,
        control_id=resolved_id,
        before_focus_id=before_focus,
        after_focus_id=after_focus,
        artifacts=_ui_artifact_refs(artifacts),
        metadata={"action": action},
    )
    return skill_success(
        "UI action completed",
        action_result=result.to_dict(),
        control=after,
        before=before,
        after=after,
        artifacts=artifacts,
    )


def capture_ui(object_name: Optional[str] = None) -> Dict[str, Any]:
    """Capture the Maya main window or a named Qt widget as base64 PNG."""

    root, widget_type, error = _maya_main_window()
    if error is not None:
        return error
    assert root is not None
    assert widget_type is not None

    widget = _find_widget(root, widget_type, object_name)
    if widget is None:
        return skill_error(
            "Qt widget not found",
            "No Maya widget matched object_name={!r}.".format(object_name),
            object_name=object_name,
        )

    tmp_path: Optional[str] = None
    try:
        pixmap = widget.grab()
        if pixmap.isNull():
            return skill_error(
                "UI capture produced an empty image",
                "Qt returned a null pixmap for the requested widget.",
                object_name=object_name,
            )
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        if not pixmap.save(tmp_path, "PNG"):
            return skill_error("UI capture failed", "Qt could not save the grabbed pixmap as PNG.")
        with open(tmp_path, "rb") as fh:
            image_bytes = fh.read()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        size = pixmap.size()
        return skill_success(
            "Maya UI captured",
            image=encoded,
            width=int(size.width()),
            height=int(size.height()),
            format="png",
            encoding="base64",
            object_name=object_name,
            widget_class=type(widget).__name__,
            widget_object_name=str(widget.objectName()),
            window_title=str(widget.windowTitle()),
        )
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to capture Maya UI")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _node_ref_from_name(node: str) -> Optional[Dict[str, Any]]:
    import maya.cmds as cmds  # noqa: PLC0415

    if not node or not cmds.objExists(node):
        return None
    long_names = cmds.ls(node, long=True) or []
    long_name = str(long_names[0]) if long_names else str(node)
    short_name = long_name.split("|")[-1]
    uuids = cmds.ls(long_name, uuid=True) or []
    node_type = cmds.nodeType(long_name) if cmds.objExists(long_name) else None
    return {
        "kind": "maya_node",
        "id": str(uuids[0]) if uuids else long_name,
        "uuid": str(uuids[0]) if uuids else None,
        "long_name": long_name,
        "short_name": short_name,
        "type": node_type,
        "exists": True,
        "stale": False,
        "metadata": {
            "scene_path": _current_scene_path(),
        },
    }


def _current_scene_path() -> Optional[str]:
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        path = cmds.file(query=True, sceneName=True)
        return str(path) if path else None
    except Exception:
        return None


def _find_node_by_uuid(uuid_value: str) -> Optional[str]:
    import maya.cmds as cmds  # noqa: PLC0415

    if not uuid_value:
        return None
    try:
        direct = cmds.ls(uuid_value, long=True) or []
        for node in direct:
            uuids = cmds.ls(node, uuid=True) or []
            if uuids and str(uuids[0]) == uuid_value:
                return str(node)
    except Exception:
        pass
    try:
        nodes = cmds.ls(long=True) or []
        uuids = cmds.ls(nodes, uuid=True) or []
        for node, node_uuid in zip(nodes, uuids):
            if str(node_uuid) == uuid_value:
                return str(node)
    except Exception:
        return None
    return None


def make_node_ref(node: str) -> Dict[str, Any]:
    """Return a stable reference payload for a Maya node."""

    try:
        ref = _node_ref_from_name(node)
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to build Maya node reference")
    if ref is None:
        return skill_error(
            "Maya node not found",
            "No node named {!r} exists in the current scene.".format(node),
            node=node,
            stale=True,
        )
    return skill_success("Maya node reference created", node_ref=ref)


def resolve_node_ref(
    ref: Optional[Dict[str, Any]] = None,
    uuid: Optional[str] = None,
    long_name: Optional[str] = None,
    short_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve a previously returned Maya node reference."""

    payload = ref if isinstance(ref, dict) else {}
    uuid_value = uuid or payload.get("uuid") or payload.get("id")
    long_value = long_name or payload.get("long_name")
    short_value = short_name or payload.get("short_name")
    try:
        candidate = _find_node_by_uuid(str(uuid_value)) if uuid_value else None
        if candidate is None and long_value:
            import maya.cmds as cmds  # noqa: PLC0415

            if cmds.objExists(str(long_value)):
                candidate = str(long_value)
        if candidate is None and short_value:
            import maya.cmds as cmds  # noqa: PLC0415

            matches = cmds.ls(str(short_value), long=True) or []
            if len(matches) == 1:
                candidate = str(matches[0])
        if candidate is None:
            stale_ref = dict(payload)
            stale_ref.update(
                {
                    "kind": "maya_node",
                    "exists": False,
                    "stale": True,
                    "uuid": uuid_value,
                    "long_name": long_value,
                    "short_name": short_value,
                }
            )
            return skill_error(
                "Maya node reference is stale",
                "The referenced node could not be resolved by UUID, long name, or short name.",
                node_ref=stale_ref,
            )
        resolved = _node_ref_from_name(candidate)
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to resolve Maya node reference")
    return skill_success("Maya node reference resolved", node_ref=resolved)


def run_check(
    target: Optional[str] = None,
    module: Optional[str] = None,
    callable: Optional[str] = None,  # noqa: A002 - public tool parameter
    args: Any = None,
    kwargs: Any = None,
    project_name: Optional[str] = None,
    reload_before: bool = True,
    reload_mode: str = "purge",
    capture_ui_image: bool = False,
    ui_object_name: Optional[str] = None,
    artifact_threshold: int = DEFAULT_ARTIFACT_THRESHOLD,
    event_session_id: Optional[str] = None,
    event_tool_call_id: Optional[str] = None,
    event_job_id: Optional[str] = None,
    event_correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Reload project code, run an entrypoint, and optionally capture Maya UI."""

    run_result = run_entrypoint(
        target=target,
        module=module,
        callable=callable,
        args=args,
        kwargs=kwargs,
        project_name=project_name,
        reload_before=reload_before,
        reload_mode=reload_mode,
        capture_output=True,
    )
    run_context = run_result.get("context", {})
    run_artifacts = _externalize_text_fields(
        run_context,
        fields=("stdout", "stderr", "traceback"),
        threshold=int(artifact_threshold or DEFAULT_ARTIFACT_THRESHOLD),
    )
    run_summary = {
        "target": run_context.get("target"),
        "elapsed_secs": run_context.get("elapsed_secs"),
        "stdout_chars": len(run_context.get("stdout") or ""),
        "stderr_chars": len(run_context.get("stderr") or ""),
        "has_traceback": bool(run_context.get("traceback")),
        "artifact_count": len(run_artifacts),
    }
    event_context = _publish_run_check_events(
        run_context,
        run_summary,
        run_artifacts,
        run_success=bool(run_result.get("success")),
        session_id=event_session_id,
        tool_call_id=event_tool_call_id,
        job_id=event_job_id,
        correlation_id=event_correlation_id,
    )
    run_summary["event_count"] = event_context["published_count"]
    ui_context: Optional[Dict[str, Any]] = None
    ui_success: Optional[bool] = None
    if capture_ui_image:
        ui_result = capture_ui(ui_object_name)
        ui_success = bool(ui_result.get("success"))
        ui_context = ui_result.get("context", ui_result)

    ctx = {
        "run": run_context,
        "run_summary": run_summary,
        "artifacts": run_artifacts,
        "observability_events": event_context,
        "run_success": bool(run_result.get("success")),
    }
    if ui_context is not None:
        ctx["ui_capture"] = ui_context
        ctx["ui_capture_success"] = ui_success
    if run_result.get("success"):
        return skill_success(
            "Development check completed",
            prompt="For viewport evidence, load maya-render and call capture_viewport after this check.",
            **ctx,
        )
    return skill_error(
        "Development check failed",
        run_result.get("message") or "Entrypoint failed",
        prompt="Inspect context.run.stdout, context.run.stderr, and context.run.traceback.",
        **ctx,
    )


def reset_for_tests() -> None:
    """Reset module state for unit tests."""

    with _LOCK:
        _STATE["active"] = None
        _STATE["projects"] = {}
        _DEBUGPY_STATE.update(
            {
                "listening": False,
                "host": None,
                "port": None,
                "log_dir": None,
                "python_executable": None,
                "path_mappings": [],
            }
        )
        _UI_STATE["refs"] = {}
        _UI_STATE["seq"] = 0
        _SESSION_EVENT_STATE.update(
            {
                "buffer": None,
                "instance_id": None,
                "resource_uri": None,
                "registered": False,
            }
        )
