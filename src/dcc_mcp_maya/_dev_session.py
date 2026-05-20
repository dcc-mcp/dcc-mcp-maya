"""Development-session helpers for MCP-assisted Maya tool authoring.

The ``maya-dev`` skill exposes these helpers as typed tools.  Keeping the
state in a package module (rather than in individual skill scripts) makes the
session survive core's per-call script loading model.
"""

from __future__ import annotations

import base64
import contextlib
import importlib
import io
import json
import os
import runpy
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

ENV_DEV_ROOTS = "DCC_MCP_MAYA_DEV_ROOTS"

_LOCK = threading.RLock()
_DEBUGPY_STATE: Dict[str, Any] = {
    "listening": False,
    "host": None,
    "port": None,
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
    matches = [
        name
        for name, module in list(sys.modules.items())
        if _matches_module(name, module, project, prefixes)
    ]
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
        return None, skill_error("No module provided", "Pass target='package.module:function' or module='package.module'.")
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
        return None, skill_error("No script path provided", "Pass script_path as a project-relative or absolute .py path.")
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


def start_debugpy(host: str = "127.0.0.1", port: int = 5678, wait_for_client: bool = False) -> Dict[str, Any]:
    """Start debugpy in the Maya process so an IDE can attach."""

    host = str(host or "127.0.0.1")
    port = int(port or 5678)
    with _LOCK:
        if _DEBUGPY_STATE.get("listening"):
            return _debugpy_status("debugpy is already listening", reused=True)

    try:
        import debugpy  # noqa: PLC0415
    except ImportError:
        return skill_error(
            "debugpy is not installed in this Maya Python environment",
            "Install debugpy into the Python interpreter used by Maya.",
            possible_solutions=[
                "Run mayapy -m pip install debugpy for the Maya version you are debugging.",
                "Restart Maya after installing debugpy, then call start_debugpy again.",
            ],
        )

    try:
        debugpy.listen((host, port))
        if wait_for_client:
            debugpy.wait_for_client()
        connected = bool(getattr(debugpy, "is_client_connected", lambda: False)())
    except RuntimeError as exc:
        message = str(exc).lower()
        if "already" not in message:
            return skill_exception(exc, message="Failed to start debugpy")
        connected = bool(getattr(debugpy, "is_client_connected", lambda: False)())

    with _LOCK:
        _DEBUGPY_STATE.update({"listening": True, "host": host, "port": port})

    return skill_success(
        "debugpy listening on {}:{}".format(host, port),
        host=host,
        port=port,
        client_connected=connected,
        wait_for_client=bool(wait_for_client),
    )


def _debugpy_status(message: str = "debugpy status", reused: bool = False) -> Dict[str, Any]:
    try:
        import debugpy  # noqa: PLC0415

        connected = bool(getattr(debugpy, "is_client_connected", lambda: False)())
    except ImportError:
        connected = False
    return skill_success(
        message,
        listening=bool(_DEBUGPY_STATE.get("listening")),
        host=_DEBUGPY_STATE.get("host"),
        port=_DEBUGPY_STATE.get("port"),
        client_connected=connected,
        reused=bool(reused),
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
        return None, None, skill_error(
            "Qt bindings are not available",
            "Maya UI capture requires PySide/PySide2/PySide6 and shiboken.",
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
    ui_context: Optional[Dict[str, Any]] = None
    ui_success: Optional[bool] = None
    if capture_ui_image:
        ui_result = capture_ui(ui_object_name)
        ui_success = bool(ui_result.get("success"))
        ui_context = ui_result.get("context", ui_result)

    ctx = {
        "run": run_context,
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
        _DEBUGPY_STATE.update({"listening": False, "host": None, "port": None})
