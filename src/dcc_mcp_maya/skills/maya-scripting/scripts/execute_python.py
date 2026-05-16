"""Bare-exec Python in Maya — same shape as PatrickPalmer/maya-mcp-server.

The implementation is intentionally **wrapper-free**:

* Persistent module-level ``globals()`` so a user's ``import x`` survives
  across calls (the next call sees ``x`` already imported, no re-import
  cost, no namespace surprises).
* AST-rewrite of the last top-level expression for result capture — the
  user does not need a ``result = ...`` convention, just leave a bare
  expression as the final line. Python 3.7+ compatible (no
  ``ast.unparse``).
* **No** ``mcp_safe_session`` (deleted in #248).
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
path that works is the one a user would type in the Script Editor —
``exec(compile(code, ...), globals_dict)``.

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
import traceback
from typing import Any, Dict, Optional, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Persistent module-level namespace for cross-call state. Same idea as
# maya-mcp-server's ``context = globals()`` — long-running sessions can
# ``import x`` once and rely on subsequent calls seeing the cached name.
_PERSISTENT_NS: Dict[str, Any] = {"__name__": "__maya_mcp_exec__"}

_VALID_RESULT_TYPES = frozenset({"NONE", "VALUE", "JSON", "REPR"})


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
) -> Dict[str, Any]:
    """Run ``code``; return the unified envelope dict.

    Envelope shape::

        {
            "success": bool,
            "result": <captured value, optional>,
            "error": {"type", "message", "traceback"} | None,
            "stdout": str,
            "stderr": str,
        }

    ``stdout`` / ``stderr`` are captured via
    :func:`contextlib.redirect_stdout` / ``redirect_stderr`` only when
    ``capture_output=True``. The redirects target pure-Python
    ``io.StringIO`` buffers; they do not touch any Maya C++ surface
    and so cannot corrupt the engine's internal state (the failure
    mode that made us delete the legacy ``MayaOutputCapture`` hook).
    """
    stdout_buf = io.StringIO() if capture_output else None
    stderr_buf = io.StringIO() if capture_output else None

    error: Optional[Dict[str, str]] = None
    result: Any = None

    with contextlib.ExitStack() as stack:
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


def _resolve_script_file_path(params: Dict[str, Any]) -> Optional[str]:
    for key in ("file_path", "script_path"):
        raw = params.get(key)
        if raw is None:
            continue
        s = str(raw).strip()
        if s:
            return s
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

    Drops every wrapper the previous revision shipped (``mcp_safe_session``,
    ``ScriptExecutionCapture`` tee, ``MayaOutputCapture`` OpenMaya
    callback bridge, ``sys.settrace`` cancellation tracer). The
    dispatch path is now what a user would type in the Script Editor —
    same as PatrickPalmer/maya-mcp-server, our stability benchmark.

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

    envelope = _execute_bare(
        code=code,
        filename=filename,
        result_type=result_type,
        capture_output=capture_output,
        namespace=run_ns,
    )

    if not envelope["success"]:
        err_info = envelope["error"] or {}
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
