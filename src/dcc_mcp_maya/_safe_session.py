"""Modal-free Maya session for MCP-dispatched jobs.

Why this exists
---------------
Every job dispatched onto Maya's UI thread by ``MayaUiDispatcher`` blocks
the main thread until it returns.  If anything during that job pops a
**modal dialog** — Maya AutoSave's "you must give the file a name to
save" prompt, ``cmds.confirmDialog``, native ``fileDialog2``, etc. — the
main thread is parked waiting for *human* input that will never arrive.
Every subsequent MCP request piles up behind it and the whole adapter
appears hung from the gateway's perspective.

The most reliable fix lives **inside** the adapter, not in every skill
script: wrap each in-process job in a context manager that:

* Snoozes Maya's AutoSave for the job's duration (``-enable false``).
* Replaces the dialog-spawning ``cmds`` entry points with non-blocking
  stubs that return a sane default and emit a structured warning to
  the script's stderr capture so the agent can see what was suppressed.
* Restores the originals on exit, even on exception.

The context is **reentrant via refcount** so nested invocations
(execute_python invoking another skill via core's executor) don't undo
each other's state.

This module is intentionally pure-Python with zero hard import on
``maya.cmds``.  When Maya is unavailable (mayapy in a unit test, plain
CPython) ``mcp_safe_session`` is a no-op, which keeps the adapter
testable from CI.

Public API
----------
``mcp_safe_session()``
    Reentrant context manager used by :mod:`dcc_mcp_maya._executor`.
``suppressed_dialog_calls()``
    Snapshot of dialog calls intercepted in the current scope (for
    tests + audit purposes).
``ENV_SAFE_SESSION``
    ``"DCC_MCP_MAYA_SAFE_SESSION"`` — set to ``"0"`` to disable the
    wrapper globally (escape hatch for skills that legitimately need to
    show a dialog, e.g. an interactive author-time helper).
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import contextlib
import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, List, Optional

logger = logging.getLogger(__name__)

ENV_SAFE_SESSION = "DCC_MCP_MAYA_SAFE_SESSION"

#: Names of ``cmds`` entry points that can spawn a modal dialog and
#: therefore deadlock the dispatcher.  Each entry maps the function name
#: to a ``default_factory`` that returns a benign value of the shape the
#: real call would produce, so callers don't crash on ``None``.
_DIALOG_FUNCTION_DEFAULTS = {
    "confirmDialog": lambda *_a, **_kw: "dismiss",
    "promptDialog": lambda *_a, **_kw: "dismiss",
    "fileDialog": lambda *_a, **_kw: "",
    "fileDialog2": lambda *_a, **_kw: [],
    "layoutDialog": lambda *_a, **_kw: "dismiss",
    # ``inViewMessage`` and ``warning`` are *not* modal but mention them
    # here so contributors know they are intentionally NOT suppressed.
}


@dataclass
class _SessionState:
    """Per-thread state for the safe-session refcount + restore plan."""

    refcount: int = 0
    autosave_was_enabled: Optional[bool] = None
    original_dialog_funcs: dict = field(default_factory=dict)
    suppressed_calls: List[str] = field(default_factory=list)


_thread_local = threading.local()


def _state() -> _SessionState:
    """Return the calling thread's ``_SessionState`` (creating it lazily)."""
    state = getattr(_thread_local, "state", None)
    if state is None:
        state = _SessionState()
        _thread_local.state = state
    return state


def suppressed_dialog_calls() -> List[str]:
    """Return the list of dialog calls suppressed in the current thread.

    Each entry is a human-readable string ``"<func_name>(<title>)"`` so
    audit / test code can verify which dialogs would have appeared.
    The list is reset every time the outermost ``mcp_safe_session``
    exits.
    """
    return list(_state().suppressed_calls)


def _is_disabled_via_env() -> bool:
    """Honor ``DCC_MCP_MAYA_SAFE_SESSION=0`` as an opt-out."""
    val = os.environ.get(ENV_SAFE_SESSION, "").strip().lower()
    return val in {"0", "false", "off", "no"}


def _import_cmds() -> Optional[Any]:
    """Return ``maya.cmds`` or ``None`` when Maya is unavailable.

    Kept private so the rest of the module never has to deal with the
    ``ImportError`` branch directly.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return None
    return cmds


def _disable_autosave(cmds: Any, state: _SessionState) -> None:
    """Snapshot + disable Maya's AutoSave for the job's duration.

    The original value is captured into ``state.autosave_was_enabled``
    so :func:`_restore_autosave` can flip it back unconditionally.  Any
    failure is swallowed and logged at DEBUG — a missing autosave
    feature must not break the dispatcher.
    """
    try:
        state.autosave_was_enabled = bool(cmds.autoSave(query=True, enable=True))
    except Exception as exc:  # noqa: BLE001 — Maya may raise nondescript errors
        logger.debug("safe-session: autoSave query failed: %s", exc)
        state.autosave_was_enabled = None
        return
    try:
        cmds.autoSave(enable=False)
    except Exception as exc:  # noqa: BLE001
        logger.debug("safe-session: autoSave disable failed: %s", exc)


def _restore_autosave(cmds: Any, state: _SessionState) -> None:
    if state.autosave_was_enabled is None:
        return
    try:
        cmds.autoSave(enable=bool(state.autosave_was_enabled))
    except Exception as exc:  # noqa: BLE001
        logger.debug("safe-session: autoSave restore failed: %s", exc)
    finally:
        state.autosave_was_enabled = None


def _make_dialog_stub(name: str, default_factory: Callable[..., Any], state: _SessionState) -> Callable[..., Any]:
    """Build a replacement for a dialog ``cmds`` entry point.

    The stub:
    1. Records the call in ``state.suppressed_calls`` (with the
       ``title=`` kwarg if provided — the most useful audit hint).
    2. Writes a one-line warning to ``sys.stderr`` so the
       :class:`MayaOutputCapture` running inside ``execute_python``
       includes it in the structured envelope returned to the agent.
    3. Returns the ``default_factory(...)`` value so the caller's code
       path keeps running.
    """

    def _stub(*args: Any, **kwargs: Any) -> Any:
        title = kwargs.get("title") or kwargs.get("t") or ""
        record = "{}({!r})".format(name, title) if title else "{}()".format(name)
        state.suppressed_calls.append(record)
        sys.stderr.write(
            "[dcc-mcp-maya] safe-session intercepted modal dialog '{}' — "
            "MCP-dispatched code may not block on user input.\n".format(record),
        )
        return default_factory(*args, **kwargs)

    _stub.__name__ = "{}__mcp_safe_stub".format(name)
    _stub.__qualname__ = _stub.__name__
    return _stub


def _install_dialog_stubs(cmds: Any, state: _SessionState) -> None:
    """Monkey-patch every dialog entry point listed in ``_DIALOG_FUNCTION_DEFAULTS``.

    Originals are saved to ``state.original_dialog_funcs`` so the exit
    path can restore them unconditionally.  When ``cmds`` lacks a given
    function (older Maya versions, headless mayapy without UI) we
    silently skip it.
    """
    for func_name, default in _DIALOG_FUNCTION_DEFAULTS.items():
        original = getattr(cmds, func_name, None)
        if original is None:
            continue
        state.original_dialog_funcs[func_name] = original
        try:
            setattr(cmds, func_name, _make_dialog_stub(func_name, default, state))
        except (TypeError, AttributeError) as exc:
            logger.debug("safe-session: cannot patch cmds.%s: %s", func_name, exc)


def _restore_dialog_stubs(cmds: Any, state: _SessionState) -> None:
    for func_name, original in state.original_dialog_funcs.items():
        try:
            setattr(cmds, func_name, original)
        except (TypeError, AttributeError) as exc:
            logger.debug("safe-session: cannot restore cmds.%s: %s", func_name, exc)
    state.original_dialog_funcs.clear()


@contextlib.contextmanager
def mcp_safe_session() -> Iterator[None]:
    """Run the wrapped block with Maya's modal-dialog hazards neutralised.

    Yields control after:
    1. AutoSave is snoozed for the duration of the block.
    2. ``cmds.confirmDialog`` / ``promptDialog`` / ``fileDialog`` /
       ``fileDialog2`` / ``layoutDialog`` are replaced with
       non-blocking stubs that emit a stderr warning and return a
       defaulted value.

    The context is **reentrant** within a single thread: nested
    invocations only re-enter the refcount; outer-most exit restores
    the originals.

    No-op when ``maya.cmds`` is unavailable or when
    ``DCC_MCP_MAYA_SAFE_SESSION=0``.
    """
    if _is_disabled_via_env():
        yield
        return

    cmds = _import_cmds()
    if cmds is None:
        yield
        return

    state = _state()
    state.refcount += 1
    if state.refcount == 1:
        state.suppressed_calls.clear()
        _disable_autosave(cmds, state)
        _install_dialog_stubs(cmds, state)
    try:
        yield
    finally:
        state.refcount -= 1
        if state.refcount == 0:
            _restore_dialog_stubs(cmds, state)
            _restore_autosave(cmds, state)


__all__ = [
    "ENV_SAFE_SESSION",
    "mcp_safe_session",
    "suppressed_dialog_calls",
]
