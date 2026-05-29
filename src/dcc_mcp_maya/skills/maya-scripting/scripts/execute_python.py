"""Bare-exec Python in Maya — same shape as PatrickPalmer/maya-mcp-server.

The implementation keeps the bare-exec shape:

* Persistent module-level ``globals()`` so a user's ``import x`` survives
  across calls (the next call sees ``x`` already imported, no re-import
  cost, no namespace surprises).
* AST-rewrite of the last top-level expression for result capture — the
  user does not need a ``result = ...`` convention, just leave a bare
  expression as the final line. Python 3.7+ compatible (no
  ``ast.unparse``).
* **No** broad ``mcp_safe_session`` dialog monkey-patch (deleted in #248).
  Only ``cmds.file`` is guarded during execution so dirty-scene file
  operations fail fast instead of opening modal prompts.
* **No** ``MayaOutputCapture`` (the C++ ``MCommandMessage`` callback bridge
  crashed Maya on idle ticks; default no-op since #248 da5f6184. Opt
  in via ``DCC_MCP_MAYA_HOOK_MAYA_OUTPUT=1`` if you really need it).
* **No** ``sys.settrace`` cancellation tracer.
* Standard ``contextlib.redirect_stdout`` / ``redirect_stderr`` for the
  optional ``capture_output=True`` path — this is pure Python and
  cannot corrupt Maya's internal state.

Why this shape
==============

We benchmark against PatrickPalmer/maya-mcp-server, which has been the
stability reference throughout RFC #998's follow-up fix series. Every
wrapper we previously added either crashed Maya in the field
(``cmds.confirmDialog`` monkey-patch, ``MCommandMessage`` callback) or
duplicated work the plug-in already does at session scope (AutoSave
snooze → persistent disable at plug-in load). The simplest dispatch
path that works is the one a user would type in the Script Editor:
``exec(compile(code, ...), globals_dict)`` plus a narrow ``cmds.file``
prompt guard around the execution window.

Public interface (kept stable)
==============================

``code`` / ``script`` / ``source``
    Inline Python. The aliases match the upstream
    ``normalize_script_execution_params`` contract from ``dcc-mcp-core``.

``file_path`` / ``script_path``
    Run a ``.py`` file with ``__file__`` / ``this_root`` set, like Maya's
    Script Editor.

``result_type``
    ``NONE`` (default, discards) / ``VALUE`` / ``JSON`` / ``REPR``.
    Selecting anything other than ``NONE`` requires the source to end
    with a standalone expression statement — otherwise an error envelope
    surfaces.

``capture_output``
    ``True`` (default) redirects ``sys.stdout`` / ``sys.stderr`` into the
    returned envelope. ``False`` lets prints reach Maya's Script Editor
    directly.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import threading
import traceback
import warnings
from typing import Any, Dict, Optional, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._cmds_file_guard import MayaFilePromptBlockedError, guard_cmds_file

_SCRIPT_PATH_DEPRECATION = "`script_path` is deprecated, use `file_path` instead."

# Maya's main thread is the only thread that can safely touch the scene
# graph / call ``maya.cmds`` / load native plug-ins. The ``execute_python``
# entry point is reached from a hyper (tokio) worker thread when an MCP
# client hits ``POST /v1/call`` — running ``cmds.file(..., type="FBX export")``
# or ``cmds.loadPlugin("fbxmaya")`` off the main thread is the canonical
# way to crash Maya (verified in #248 with the user's batch FBX script).
#
# This module captures the main thread at import time so the runtime
# can compare ``threading.current_thread()`` against it and route to
# ``maya.utils.executeInMainThreadWithResult`` when needed.
_MAIN_THREAD = threading.main_thread()

# Persistent module-level namespace for cross-call state. Same idea as
# maya-mcp-server's ``context = globals()`` — long-running sessions can
# ``import x`` once and rely on subsequent calls seeing the cached name.
_PERSISTENT_NS: Dict[str, Any] = {"__name__": "__maya_mcp_exec__"}

_VALID_RESULT_TYPES = frozenset({"NONE", "VALUE", "JSON", "REPR"})


def _ensure_maya_aliases(namespace: Dict[str, Any]) -> None:
    """Lazily inject the ``cmds`` / ``mel`` aliases and node helpers users expect.

    maya-mcp-server (our stability benchmark) executes against
    ``globals()`` of a module that already does
    ``import maya.cmds as cmds``. Users typing scripts in the Script
    Editor write ``cmds.polyCube(...)`` without an explicit import.
    Reproduce that ergonomic by pre-populating the persistent
    namespace on first use. Imports are best-effort — when Maya is
    unavailable (``mayapy``/tests with no mock) the aliases simply
    stay absent and user code has to qualify ``maya.cmds`` itself.
    """
    if "cmds" not in namespace:
        try:
            import maya.cmds as _cmds  # noqa: PLC0415
        except ImportError:
            pass
        else:
            namespace["cmds"] = _cmds
    if "mel" not in namespace:
        try:
            import maya.mel as _mel  # noqa: PLC0415
        except ImportError:
            pass
        else:
            namespace["mel"] = _mel

    def _require_cmds_alias() -> Any:
        cmds = namespace.get("cmds")
        if cmds is None:
            raise RuntimeError("maya.cmds is not available in this execution namespace")
        return cmds

    if "maya_node_summary" not in namespace:
        from dcc_mcp_maya.api import summarize_node  # noqa: PLC0415

        def _maya_node_summary(node_name: str) -> Dict[str, Any]:
            return summarize_node(_require_cmds_alias(), node_name)

        namespace["maya_node_summary"] = _maya_node_summary

    if "maya_created_object_context" not in namespace:
        from dcc_mcp_maya.api import created_object_context  # noqa: PLC0415

        def _maya_created_object_context(result: Any, requested_name: Optional[str] = None) -> Dict[str, Any]:
            return created_object_context(_require_cmds_alias(), result, requested_name)

        namespace["maya_created_object_context"] = _maya_created_object_context


def _exec_and_capture_last_expression(code: str, filename: str, namespace: Dict[str, Any]) -> Tuple[Any, bool]:
    """Exec ``code`` on ``namespace``; return ``(value, was_expression)``.

    If the last AST node is an :class:`ast.Expr` statement, its value is
    captured via ``compile(..., 'eval') + eval(...)`` after the rest of
    the body is exec'd as a regular module. This avoids
    ``ast.unparse`` (Python 3.9+) so the implementation is
    Python 3.7-clean for Maya 2022.

    Works for one statement or many; degrades to a bare ``exec`` for
    bodies whose final statement is an assignment / control flow / def
    (``was_expression=False`` in that case so callers know not to look
    for a value).
    """
    tree = ast.parse(code, filename=filename, mode="exec")
    if not tree.body:
        return None, False

    last = tree.body[-1]
    if isinstance(last, ast.Expr):
        head_nodes = tree.body[:-1]
        if head_nodes:
            head_module = ast.Module(
                body=head_nodes,
                type_ignores=getattr(tree, "type_ignores", []),
            )
            exec(  # noqa: S102 — execute_python is the bare-exec entry point
                compile(head_module, filename, "exec"),
                namespace,
            )
        eval_code = compile(ast.Expression(body=last.value), filename, "eval")
        value = eval(eval_code, namespace)  # noqa: S307
        return value, True

    exec(compile(tree, filename, "exec"), namespace)  # noqa: S102
    return None, False


def _coerce_result(value: Any, result_type: str) -> Any:
    """Apply the requested representation to a captured value.

    ``NONE`` returns ``None`` (discard). ``VALUE`` passes through if the
    object is JSON-serialisable, else falls back to ``repr`` so the
    envelope is always JSON-safe. ``JSON`` round-trips through ``json``.
    ``REPR`` returns ``repr(value)``.
    """
    if result_type == "NONE":
        return None
    if result_type == "REPR":
        return repr(value)
    if result_type == "JSON":
        try:
            return json.loads(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return repr(value)
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def _execute_bare(
    code: str,
    filename: str,
    result_type: str,
    capture_output: bool,
    namespace: Dict[str, Any],
    inplace: bool = False,
) -> Dict[str, Any]:
    """Route user code to Maya's main thread when needed, then run it.

    The MCP entry point reaches ``execute_python`` from a hyper (tokio)
    worker thread when a client hits ``POST /v1/call``. Running
    ``cmds.file(..., type="FBX export")`` / ``cmds.loadPlugin(...)`` /
    most scene-mutating ``cmds.*`` calls off the main thread crashes
    Maya — verified against the user's batch FBX script in #248.

    The fix mirrors what every well-behaved Maya plug-in does for
    cross-thread work: wrap the call in
    :func:`maya.utils.executeInMainThreadWithResult`. The wrapper:

    * **Already on main thread** — runs inline (the deferred call would
      deadlock itself).
    * **No Maya available** — runs inline (``mayapy`` / pytest fallback,
      no UI thread to defer to).
    * **inplace=True** — caller has explicitly opted out (used by tests
      and by callers that have already been promoted to main thread by
      an outer dispatcher).
    * **Otherwise** — marshals the bare-exec call onto Maya's main
      thread via ``executeInMainThreadWithResult`` and waits for the
      result. The caller (hyper worker) is blocked for the duration,
      same as every ``cmds.file`` call would have been if dispatched
      directly.

    Why not ``executeDeferred``
    ---------------------------

    ``executeDeferred`` is fire-and-forget — schedules the call and
    returns immediately. The MCP request is synchronous by definition,
    so blocking the worker thread until the result is back is the
    correct shape. The Maya main thread is otherwise idle inside the
    UI event loop, so the marshalling round-trip is essentially free.

    ``executeInMainThreadWithResult`` is the documented Maya primitive
    for this and is what ``maya-mcp-server`` (PatrickPalmer / chadrik)
    uses at the user-code boundary. Aligning with that reference is
    the whole point of #248.
    """
    if inplace or _running_on_main_thread() or not _should_marshal_to_maya_main_thread():
        return _execute_bare_inplace(code, filename, result_type, capture_output, namespace)

    # Hand off to the process-wide single-writer queue. The pump thread
    # serialises every concurrent ``execute_python`` invocation through
    # ``maya.utils.executeInMainThreadWithResult`` so:
    #   * order is strict FIFO (independent of tokio scheduling),
    #   * only one main-thread bridge call is in flight at a time
    #     (no thrash on Maya's deferred queue under burst load),
    #   * the queue has a bounded depth (configurable via
    #     ``DCC_MCP_MAYA_EXEC_QUEUE_DEPTH``), so floods surface as a
    #     clean ``QueueFullError`` envelope instead of stalling tokio
    #     workers indefinitely.
    from dcc_mcp_maya import _main_thread_queue  # noqa: PLC0415

    def _on_main() -> Dict[str, Any]:
        return _execute_bare_inplace(code, filename, result_type, capture_output, namespace)

    future = _main_thread_queue.get_queue().submit(_on_main)
    try:
        return future.result()
    except _main_thread_queue.QueueFullError as exc:
        return {
            "success": False,
            "result": None,
            "error": {"type": "QueueFullError", "message": str(exc), "traceback": ""},
            "stdout": "",
            "stderr": "",
        }
    except Exception as exc:  # noqa: BLE001 — relay marshalling / pump failure
        return {
            "success": False,
            "result": None,
            "error": {
                "type": "{0}.{1}".format(type(exc).__module__, type(exc).__name__),
                "message": (
                    "executeInMainThreadWithResult failed to marshal user code onto Maya's main thread: {0}".format(exc)
                ),
                "traceback": traceback.format_exc(),
            },
            "stdout": "",
            "stderr": "",
        }


def _execute_bare_inplace(
    code: str,
    filename: str,
    result_type: str,
    capture_output: bool,
    namespace: Dict[str, Any],
) -> Dict[str, Any]:
    """Run ``code`` on the **current** thread without any main-thread marshalling.

    This is the inner-most execution primitive. The :func:`_execute_bare`
    wrapper above decides which thread to run on. ``_execute_bare_inplace``
    only knows how to ``exec`` against the given namespace and capture
    output — it never touches Maya's threading machinery.
    """
    stdout_buf = io.StringIO() if capture_output else None
    stderr_buf = io.StringIO() if capture_output else None

    error: Optional[Dict[str, str]] = None
    result: Any = None

    with contextlib.ExitStack() as stack:
        stack.enter_context(guard_cmds_file(namespace.get("cmds")))
        if stdout_buf is not None:
            stack.enter_context(contextlib.redirect_stdout(stdout_buf))
        if stderr_buf is not None:
            stack.enter_context(contextlib.redirect_stderr(stderr_buf))
        try:
            value, was_expression = _exec_and_capture_last_expression(code, filename, namespace)
        except BaseException as exc:  # noqa: BLE001 — relay to client envelope
            error = {
                "type": "{0}.{1}".format(type(exc).__module__, type(exc).__name__),
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        else:
            if result_type != "NONE":
                if not was_expression:
                    error = {
                        "type": "RuntimeError",
                        "message": (
                            "result_type={0!r} requested but the source does not "
                            "end with a standalone expression. Drop the trailing "
                            "assignment / control statement, or set "
                            "result_type='NONE' to discard the return value.".format(result_type)
                        ),
                        "traceback": "",
                    }
                else:
                    result = _coerce_result(value, result_type)

    return {
        "success": error is None,
        "result": result,
        "error": error,
        "stdout": stdout_buf.getvalue() if stdout_buf is not None else "",
        "stderr": stderr_buf.getvalue() if stderr_buf is not None else "",
    }


def _running_on_main_thread() -> bool:
    """True when the current thread is Maya's UI / main thread."""
    return threading.current_thread() is _MAIN_THREAD


def _should_marshal_to_maya_main_thread() -> bool:
    """Return true only when a live Maya UI thread bridge is available.

    ``mayapy`` batch has Maya modules but no UI event loop to service
    ``executeInMainThreadWithResult``.  In that environment the HTTP
    worker thread is the only viable executor, so run inline instead of
    queueing work that core will eventually cancel.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        cmds = None
    if cmds is not None:
        try:
            if bool(cmds.about(batch=True)):
                return False
        except Exception:  # noqa: BLE001
            return False

    from dcc_mcp_maya import _main_thread_queue  # noqa: PLC0415

    utils = _main_thread_queue._import_maya_utils()  # noqa: SLF001
    return utils is not None and hasattr(utils, "executeInMainThreadWithResult")


def _resolve_script_file_path(params: Dict[str, Any]) -> Optional[str]:
    file_path = params.get("file_path")
    if file_path is not None:
        cleaned = str(file_path).strip()
        if cleaned:
            return cleaned
    # ``script_path`` is the deprecated alias kept for one release while
    # callers migrate to ``file_path`` (issue #311). It only resolves when
    # ``file_path`` is empty, and emits a ``DeprecationWarning`` so external
    # MCP clients still sending it get a clear migration signal before the
    # alias is dropped here and in the dcc-mcp-core wire schema.
    script_path = params.get("script_path")
    if script_path is not None:
        cleaned = str(script_path).strip()
        if cleaned:
            warnings.warn(_SCRIPT_PATH_DEPRECATION, DeprecationWarning, stacklevel=2)
            return cleaned
    return None


def _load_script_file(file_arg: str) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """Read a ``.py`` file from disk; return ``(code, filename, err)``."""
    expanded = os.path.abspath(os.path.expanduser(str(file_arg).strip()))
    if not os.path.isfile(expanded):
        return (
            "",
            expanded,
            skill_error(
                "Script file not found",
                expanded,
                possible_solutions=["Check file_path is readable from the Maya process."],
            ),
        )
    if not expanded.lower().endswith(".py"):
        return (
            "",
            expanded,
            skill_error(
                "file_path must be a .py file",
                expanded,
                possible_solutions=["Use execute_mel with file_path for .mel scripts."],
            ),
        )
    try:
        with open(expanded, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError as exc:
        return (
            "",
            expanded,
            skill_error("Could not read script file", str(exc), path=expanded),
        )
    return body, expanded, None


def execute_python(**params: Any):
    """Execute Python in Maya (bare exec, persistent namespace).

    Drops every broad wrapper the previous revision shipped
    (``mcp_safe_session``, ``ScriptExecutionCapture`` tee,
    ``MayaOutputCapture`` OpenMaya callback bridge, ``sys.settrace``
    cancellation tracer). The dispatch path is still what a user would type in
    the Script Editor, with a narrow ``cmds.file`` prompt guard around the exec
    window.

    See the module docstring for the parameter contract.
    """
    from dcc_mcp_maya._env import (  # noqa: PLC0415
        ENV_DISABLE_ARBITRARY_SCRIPT,
        ENV_DISABLE_EXECUTE_PYTHON,
        resolve_execute_python_disabled,
    )

    if resolve_execute_python_disabled():
        return skill_error(
            "execute_python is disabled by operator policy",
            "Unset {0} or {1} to re-enable arbitrary Python execution.".format(
                ENV_DISABLE_EXECUTE_PYTHON,
                ENV_DISABLE_ARBITRARY_SCRIPT,
            ),
            possible_solutions=[
                "Use search_skills / dcc_capability_manifest → load_skill → typed tool.",
                "Use introspect_* tools when only API discovery is needed.",
            ],
        )

    file_arg = _resolve_script_file_path(params)
    if file_arg is not None:
        code, filename, err = _load_script_file(file_arg)
        if err is not None:
            return err
        run_ns: Dict[str, Any] = __import__("__main__").__dict__
        run_ns.setdefault("this_root", os.path.dirname(filename))
        run_ns["__file__"] = filename
    else:
        code = params.get("code") or params.get("script") or params.get("source") or ""
        if not str(code).strip():
            return skill_error(
                "No Python code provided",
                "Provide non-empty source via `code` or `file_path`.",
                possible_solutions=[
                    "Inline: execute_python(code='cmds.polyCube()')",
                    "From a file: execute_python(file_path='/abs/path/to/script.py')",
                ],
            )
        filename = "<maya-mcp-exec>"
        run_ns = _PERSISTENT_NS

    result_type = str(params.get("result_type", "NONE")).upper()
    if result_type not in _VALID_RESULT_TYPES:
        return skill_error(
            "Invalid result_type",
            "Allowed values: " + ", ".join(sorted(_VALID_RESULT_TYPES)),
        )

    capture_output = bool(params.get("capture_output", True))
    inplace = bool(params.get("inplace", False))

    _ensure_maya_aliases(run_ns)

    envelope = _execute_bare(
        code=code,
        filename=filename,
        result_type=result_type,
        capture_output=capture_output,
        namespace=run_ns,
        inplace=inplace,
    )

    if not envelope["success"]:
        err_info = envelope["error"] or {}
        if str(err_info.get("type", "")).endswith("MayaFilePromptBlockedError"):
            return skill_error(
                "cmds.file prompt blocked",
                err_info.get("message", "cmds.file would have opened a modal prompt"),
                possible_solutions=[
                    "Save the current scene first.",
                    "Pass force=True when discarding unsaved changes is intentional.",
                    "Rename the scene before calling cmds.file(save=True).",
                ],
                stdout=envelope["stdout"],
                stderr=envelope["stderr"],
                error_type=MayaFilePromptBlockedError.__name__,
            )
        return skill_exception(
            RuntimeError(err_info.get("message", "unknown")),
            message="Python execution failed",
            stdout=envelope["stdout"],
            stderr=envelope["stderr"] + ("\n" + err_info.get("traceback", "") if err_info.get("traceback") else ""),
            error_type=err_info.get("type", "RuntimeError"),
        )

    return skill_success(
        "Python executed successfully",
        prompt="Python script finished. Check 'output' for any return value.",
        output=str(envelope["result"]) if envelope["result"] is not None else "",
        stdout=envelope["stdout"],
        stderr=envelope["stderr"],
    )


@skill_entry
def main(**kwargs) -> dict:
    """Skill entry — delegates to :func:`execute_python`."""
    return execute_python(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
