"""In-process skill executor (issue #127).

Extracted from the previous monolithic ``server.py``.  Core owns skill routing
through ``HostExecutionBridge`` and the global in-process executor.

This module keeps the direct script runner used by the bridge, tests, and
internal helpers.

Dispatch routing
================

:func:`execute_in_process` is the single fan-in point for every skill
action dispatched through the MCP HTTP server. It decides which thread
the action runs on by combining the ``tools.yaml`` ``affinity`` field
with the current thread context:

==========================  ===================  =====================================
``affinity`` (tools.yaml)   Current thread       Dispatch route
==========================  ===================  =====================================
``any``                     any                  inline (worker thread is OK)
``main`` *(default)*        already main         inline (no marshalling needed)
``main``                    worker + dispatcher  ``_maya_dispatcher.submit_callable``
``main``                    worker, no disp.     **main-thread queue** (safety net)
==========================  ===================  =====================================

The last row is the safety net introduced for the RFC #998 follow-up
(2026-05-16): when the ``MayaUiDispatcher`` is not attached yet (early
plug-in startup, ``mayapy`` batch mode, broken pump) we still route the
callable through :mod:`dcc_mcp_maya._main_thread_queue` rather than
crashing Maya by calling ``cmds.*`` on a hyper worker thread. The queue
internally uses :func:`maya.utils.executeInMainThreadWithResult`, which
is the documented Maya primitive for cross-thread dispatch and the same
one ``execute_python`` already uses.

The default :data:`_affinity.DEFAULT_AFFINITY` is ``"main"`` — actions
whose ``tools.yaml`` is missing / malformed / silent on ``affinity`` are
treated as main-thread-only. Mis-declaring a Maya-touching action as
``any`` would crash Maya; mis-declaring a pure action as ``main`` only
costs a main-thread tick. ``main`` is the Hippocratic default.

See: https://github.com/loonghao/dcc-mcp-maya/issues/127
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import contextlib
import logging
import threading
from typing import Any, Dict, Iterator

# Import third-party modules
from dcc_mcp_core.skill import skill_error, skill_exception

# Import local modules
from dcc_mcp_maya import _affinity

logger = logging.getLogger(__name__)

_busy_lock = threading.Lock()
_busy_count = 0

# Captured at import time so we can compare ``threading.current_thread()``
# against it. Maya plug-in / mayapy / pytest all import this module from
# the main thread, so this is the right sentinel for "is this the Maya
# UI thread?" — matches the convention in ``execute_python``.
_MAIN_THREAD = threading.main_thread()


def _on_main_thread() -> bool:
    """True when the current thread is Python's main thread (= Maya UI thread)."""
    return threading.current_thread() is _MAIN_THREAD


@contextlib.contextmanager
def _busy_scope() -> Iterator[None]:
    global _busy_count
    with _busy_lock:
        _busy_count += 1
    try:
        yield
    finally:
        with _busy_lock:
            _busy_count = max(0, _busy_count - 1)


def is_busy() -> bool:
    """Return True while an in-process Maya skill script is executing."""
    with _busy_lock:
        return _busy_count > 0


def run_skill_script(script_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run a skill script and mark the in-process executor busy.

    Previous revisions wrapped every dispatched job in
    ``mcp_safe_session`` to neutralise Maya's modal dialogs
    (AutoSave save-prompt, ``confirmDialog``, ``fileDialog2``). That
    helper has been retired (RFC #998 follow-up 2026-05-16) because
    intercepting Maya's ``cmds.*`` dialog surface crashed the engine
    on common scripts (``cmds.file(new=True)``, Arnold renderer
    switch). The plug-in now disables Maya's AutoSave timer
    persistently for the duration of the session at load time
    (see :func:`maya.plugin.dcc_mcp_maya_plugin._disable_autosave_for_session`),
    which closes the modal-AutoSave dispatch gap without monkey-
    patching anything the engine consults internally. The
    ``cmds.*`` dialog surface is left alone — same approach as
    PatrickPalmer/maya-mcp-server.
    """
    with _busy_scope():
        return _run_skill_script_untracked(script_path, params)


def _run_skill_script_untracked(script_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Load and execute a skill script in the current Python process.

    Implements the ``main(**params)`` calling convention used by all
    ``dcc-mcp-maya`` skill scripts.  The ``if __name__ == "__main__":
    run_main(main)`` guard is intentionally **not** triggered so
    parameters are forwarded directly without going through subprocess
    stdout.

    Parameters
    ----------
    script_path:
        Path to the skill Python script.
    params:
        Keyword arguments forwarded to ``main(**params)``.

    Returns
    -------
    dict
        The ``{"success": ..., "message": ..., ...}`` result dict
        (or whatever shape the skill's ``main`` produced).
    """
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("_maya_skill_script", script_path)
    if spec is None or spec.loader is None:
        return {"success": False, "message": "Cannot load skill script: {}".format(script_path)}

    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Error loading skill script: {}".format(script_path))

    if hasattr(mod, "__mcp_result__"):
        return mod.__mcp_result__  # type: ignore[return-value]

    main_fn = getattr(mod, "main", None)
    if main_fn is None:
        return {
            "success": False,
            "message": "Skill script has no main() entry point: {}".format(script_path),
        }

    try:
        result = main_fn(**params)
        return result if isinstance(result, dict) else {"success": True, "message": str(result)}
    except SystemExit:
        return getattr(mod, "__mcp_result__", {"success": True, "message": "Script executed"})
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc)


def _normalize_dispatcher_result(result: Any, action_name: str) -> Dict[str, Any]:
    """Unwrap the ``MayaUiDispatcher.submit_callable`` return envelope.

    The dispatcher wraps the user callable's result in
    ``{"success": bool, "output": <callable_return>, "error": <str>}``.
    We pull ``output`` out when present so the MCP layer sees the
    skill's own envelope, not the dispatcher's. Anything that doesn't
    fit the contract becomes a structured failure envelope rather
    than an Internal Error.
    """
    if isinstance(result, dict):
        output = result.get("output")
        if isinstance(output, dict):
            return output
        if not result.get("success", True):
            return {
                "success": False,
                "message": result.get("error") or "Dispatcher returned failure for {}".format(action_name),
            }
        if output is not None:
            return {"success": True, "message": str(output)}
    return {
        "success": False,
        "message": "Dispatcher returned unexpected result for {}".format(action_name),
    }


def _run_via_main_thread_queue(script_path: str, params: Dict[str, Any], action_name: str) -> Dict[str, Any]:
    """Marshal a skill script onto Maya's UI thread via the universal queue.

    Safety-net path for ``affinity: main`` skills when the
    ``MayaUiDispatcher`` is not attached. The queue serialises every
    such call through one pump thread that uses
    ``maya.utils.executeInMainThreadWithResult`` under the hood — the
    documented Maya primitive for cross-thread dispatch.

    Returns a structured envelope on queue overflow / marshalling
    failure rather than raising, so the MCP layer always sees a
    JSON-serialisable dict.
    """
    # Imported lazily to avoid pulling the queue module into ``mayapy``
    # paths that never go off main thread (the queue spawns a daemon
    # pump thread on first ``submit``).
    from dcc_mcp_maya import _main_thread_queue  # noqa: PLC0415

    fut = _main_thread_queue.get_queue().submit(lambda: run_skill_script(script_path, params))
    try:
        return fut.result()
    except _main_thread_queue.QueueFullError as exc:
        logger.warning("Main-thread queue full while dispatching %s: %s", action_name, exc)
        return skill_error(
            "Main-thread queue is full",
            str(exc),
            possible_solutions=[
                "Back off and retry — burst load currently exceeds queue depth.",
                "Increase DCC_MCP_MAYA_EXEC_QUEUE_DEPTH (default 64) for sustained bursts.",
                "Check io action=status for the live queue depth.",
            ],
            action=action_name,
        )
    except BaseException as exc:  # noqa: BLE001 — relay everything
        return skill_exception(
            exc,
            message="Main-thread queue failed to dispatch {}".format(action_name),
        )


def execute_in_process(
    server_obj: Any,
    script_path: str,
    params: Dict[str, Any],
    action_name: str,
) -> Dict[str, Any]:
    """Execute a skill script with thread-affinity enforcement.

    Routing order (single source of truth — see module docstring):

    1. ``affinity: any``  → run inline on the calling thread.
    2. Already on Maya's main thread → run inline (no marshalling).
    3. ``MayaUiDispatcher`` available → ``submit_callable(affinity="main")``.
       Preferred path: preserves the dispatcher's job context (cancellation
       token, telemetry, timeouts).
    4. **Safety net** — fall back to the universal
       :mod:`dcc_mcp_maya._main_thread_queue`. The queue marshals via
       ``maya.utils.executeInMainThreadWithResult`` so ``cmds.*`` /
       ``loadPlugin`` / scene mutations stay on the UI thread even when
       the dispatcher hasn't been attached (early plug-in startup,
       ``mayapy`` batch, broken pump, third-party plug-in load order).

    The ``server_obj`` argument is the :class:`MayaMcpServer` instance
    (a ``DccServerBase``); we only access ``_maya_dispatcher`` so a
    duck-typed object suffices for testing.
    """
    affinity = _affinity.resolve_affinity(script_path)

    # 1. ``affinity: any`` is the explicit opt-out — these actions are
    #    declared safe to run on a worker thread (introspect_*, pure
    #    filesystem helpers). The agent contract is documented in
    #    AGENTS.md; mis-declaring is a skill-author bug.
    if affinity != "main":
        return run_skill_script(script_path, params)

    # 2. Already on Maya's UI thread — running through the dispatcher /
    #    queue would deadlock waiting for ourselves. This is the common
    #    case in mayapy / pytest where the HTTP worker IS the main thread.
    if _on_main_thread():
        return run_skill_script(script_path, params)

    # 3. Preferred path: dispatcher (cancellation token, job context).
    dispatcher = getattr(server_obj, "_maya_dispatcher", None)
    if dispatcher is not None and hasattr(dispatcher, "submit_callable"):
        # Issue #151 — surface dispatcher-side exceptions (cancellation,
        # main-thread crashes, timeouts) as structured envelopes instead
        # of letting them propagate as Internal Errors.
        try:
            result = dispatcher.submit_callable(
                action_name,
                lambda: run_skill_script(script_path, params),
                affinity="main",
            )
        except BaseException as exc:  # noqa: BLE001 — relay everything
            return skill_exception(
                exc,
                message="Dispatcher failed to execute {}".format(action_name),
            )
        return _normalize_dispatcher_result(result, action_name)

    # 4. Safety net — dispatcher absent / unusable but we are off the
    #    main thread and the action needs the UI thread. Queue it.
    logger.debug(
        "Dispatcher unavailable; routing %s via main-thread queue (safety net)",
        action_name,
    )
    return _run_via_main_thread_queue(script_path, params, action_name)
