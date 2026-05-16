"""Modal-free Maya session for MCP-dispatched jobs.

Why this exists
---------------
Every job dispatched onto Maya's UI thread by ``MayaUiDispatcher`` blocks
the main thread until it returns. If anything during that job pops a
**modal dialog** — Maya AutoSave's "you must give the file a name to
save" prompt being the canonical example — the main thread is parked
waiting for *human* input that will never arrive. Every subsequent MCP
request piles up behind it and the whole adapter appears hung from the
gateway's perspective.

The first attempt to neutralise this risk monkey-patched
``cmds.confirmDialog`` / ``promptDialog`` / ``fileDialog`` /
``fileDialog2`` / ``layoutDialog`` with stubs that returned a fixed
``"dismiss"`` value. That worked in unit tests but **crashed Maya in
production** for several common code paths (RFC #998 follow-up,
reported 2026-05-16):

* ``cmds.file(new=True, force=True)`` triggers internal C++ callbacks
  that consult ``cmds.confirmDialog`` for asset-resolution / unsaved-
  changes prompts. The C++ side expects ``"Yes"`` / ``"No"`` /
  ``"Cancel"`` from the dialog return value — never ``"dismiss"``. The
  stub returned ``"dismiss"``, the C++ state machine took an undefined
  branch, and Maya SEGV'd on the next idle tick.
* Switching ``defaultRenderGlobals.currentRenderer`` to ``"arnold"``
  drives Maya's renderer-switch UI logic which also probes
  ``cmds.confirmDialog`` internally for plug-in load consent.
* ``cmds.fileDialog2`` is similarly consumed by Maya's reference /
  workspace machinery in ways that are not user-script-visible.

The reference impl we benchmark against (``PatrickPalmer/maya-mcp-server``
and ``chadrik/maya-mcp-server``) does **no** dialog patching and is
visibly more stable on these same scripts. The lesson is that
intercepting ``cmds.*`` globally for the duration of a dispatch is a
sledgehammer that breaks Maya's internal invariants more than it
helps the dispatcher.

What this module does now
=========================

* **Snoozes Maya's AutoSave for the job's duration** (``autoSave -enable
  false``). This is a real Maya state change that does not violate any
  internal invariants — AutoSave is documented as user-controllable —
  so it is safe to flip per job. AutoSave is the one feature that
  ACTUALLY pops modal dialogs unprompted (e.g. "Cannot AutoSave
  because the scene has unsaved changes"); snoozing it is the cheapest
  fix for the original failure mode.

* **Does NOT replace any ``cmds.*`` dialog functions.** If a skill
  script (or Maya itself) genuinely needs to spawn a dialog, the
  dialog spawns. The risk of an MCP-dispatched job hanging on a
  human-input dialog is real but rare in practice, and the right
  mitigation is a **server-side timeout** (cancel the job after N
  seconds and surface ``cancelled`` to the agent), not a global
  ``cmds.*`` monkey-patch.

* **Is reentrant via refcount** so nested invocations (a skill calling
  another skill via core's executor) don't undo each other's AutoSave
  state.

Backward compatibility
======================

``mcp_safe_session()`` keeps its name and reentrant-context-manager
shape so :mod:`dcc_mcp_maya._executor` does not need to change. The
public ``suppressed_dialog_calls()`` accessor is retained and now
always returns an empty list — the audit surface is preserved for
downstream consumers that imported it but the underlying capture is
gone with the monkey-patch.

Opt-out
=======

``DCC_MCP_MAYA_SAFE_SESSION=0`` (or ``off``/``false``/``no``) disables
even the AutoSave snooze — escape hatch for skills that legitimately
need AutoSave to fire during a long-running job.

Public API
----------
``mcp_safe_session()``
    Reentrant context manager used by :mod:`dcc_mcp_maya._executor`.
``suppressed_dialog_calls()``
    Retained for source-compat. Always ``[]`` now.
``ENV_SAFE_SESSION``
    ``"DCC_MCP_MAYA_SAFE_SESSION"`` — set to ``"0"`` to disable the
    autosave-snooze wrapper globally.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import contextlib
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Iterator, List, Optional

logger = logging.getLogger(__name__)

ENV_SAFE_SESSION = "DCC_MCP_MAYA_SAFE_SESSION"


@dataclass
class _SessionState:
    """Per-thread state for the safe-session refcount + restore plan."""

    refcount: int = 0
    autosave_was_enabled: Optional[bool] = None


_thread_local = threading.local()


def _state() -> _SessionState:
    """Return the calling thread's ``_SessionState`` (creating it lazily)."""
    state = getattr(_thread_local, "state", None)
    if state is None:
        state = _SessionState()
        _thread_local.state = state
    return state


def suppressed_dialog_calls() -> List[str]:
    """Retained for source-compat with older callers.

    Always returns ``[]`` since the dialog monkey-patch was removed in
    the 2026-05-16 stability fix. New code should not rely on this
    helper — the audit surface for "dialog suppressed during dispatch"
    no longer exists because we no longer suppress dialogs.
    """
    return []


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
    so :func:`_restore_autosave` can flip it back unconditionally. Any
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


@contextlib.contextmanager
def mcp_safe_session() -> Iterator[None]:
    """Run the wrapped block with Maya's AutoSave snoozed.

    The context manager:

    1. Snapshots Maya's current AutoSave-enabled flag.
    2. Disables AutoSave for the duration of the block.
    3. Restores the original AutoSave state on exit, even on exception.

    It is **reentrant** within a single thread: nested invocations only
    re-enter the refcount; outer-most exit restores the original state.

    No-op when ``maya.cmds`` is unavailable or when
    ``DCC_MCP_MAYA_SAFE_SESSION=0``.

    Dialog suppression history
    --------------------------

    Previous revisions of this context also monkey-patched
    ``cmds.confirmDialog`` / ``promptDialog`` / ``fileDialog`` /
    ``fileDialog2`` / ``layoutDialog`` to non-blocking stubs returning
    a fixed ``"dismiss"`` value. That suppression crashed Maya for
    several real-world scripts because Maya's C++ side consults the
    same ``cmds.*`` entry points internally and expects specific
    return values (``"Yes"`` / ``"No"`` / file paths) the stub did not
    provide. The patch was removed 2026-05-16. The mitigation for an
    MCP-dispatched job that genuinely opens a modal dialog is now a
    server-side request timeout, not a global ``cmds.*`` override.
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
        _disable_autosave(cmds, state)
    try:
        yield
    finally:
        state.refcount -= 1
        if state.refcount == 0:
            _restore_autosave(cmds, state)


__all__ = [
    "ENV_SAFE_SESSION",
    "mcp_safe_session",
    "suppressed_dialog_calls",
]
