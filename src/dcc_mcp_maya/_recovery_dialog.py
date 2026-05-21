"""Qt-level Maya recovery dialog detection (issue #241).

Maya can raise its own C++/Qt crash-recovery reporter without going through
``maya.cmds``. The MCP server may keep answering while the artist's UI is
blocked behind that modal dialog. This module is intentionally tiny and
best-effort: poll top-level Qt widgets, optionally dismiss a matching reporter,
and surface a durable status flag to agents.
"""

from __future__ import annotations

# Import built-in modules
import copy
import logging
import os
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

ENV_AUTO_DISMISS_CRASH_DIALOG = "DCC_MCP_MAYA_AUTO_DISMISS_CRASH_DIALOG"

_STATUS_DETECTED = "recovery_dialog_detected"
_STATUS_RECOVERED = "recovered"

_BUTTON_MARKERS = (
    "ok",
    "close",
    "dismiss",
    "reopen",
    "continue",
    "确定",
    "关闭",
    "重新打开",
    "继续",
)

_state_lock = threading.RLock()
_last_event: Optional[Dict[str, Any]] = None


def resolve_auto_dismiss(flag: Optional[bool] = None) -> bool:
    """Resolve the opt-in automatic dialog dismissal flag."""
    if flag is not None:
        return bool(flag)
    return os.environ.get(ENV_AUTO_DISMISS_CRASH_DIALOG, "").strip().lower() in {"1", "true", "yes", "on"}


def scan_recovery_dialog(
    qt_widgets: Optional[Any] = None,
    auto_dismiss: Optional[bool] = None,
) -> Dict[str, Any]:
    """Scan Qt top-level windows for Maya's recovery/crash reporter dialog.

    The optional ``qt_widgets`` parameter exists for tests; production calls
    lazily import PySide/PyQt from Maya.
    """
    event = _scan_recovery_dialog(qt_widgets=qt_widgets, auto_dismiss=auto_dismiss)
    if event.get("detected") or event.get("status") == _STATUS_RECOVERED:
        _record_event(event)
    return event


def current_recovery_status() -> Dict[str, Any]:
    """Return the latest Maya recovery status fields for result contexts."""
    with _state_lock:
        if not _last_event:
            return {}
        event = copy.deepcopy(_last_event)

    return {
        "maya_recovered": True,
        "maya_status": event.get("status") or _STATUS_DETECTED,
        "maya_recovery_dialog": event,
    }


def clear_recovery_status() -> None:
    """Clear the remembered recovery status."""
    global _last_event
    with _state_lock:
        _last_event = None


def poll_and_annotate_result(
    result: Dict[str, Any],
    qt_widgets: Optional[Any] = None,
    auto_dismiss: Optional[bool] = None,
) -> Dict[str, Any]:
    """Poll for a recovery dialog and annotate a skill result envelope."""
    try:
        scan_recovery_dialog(qt_widgets=qt_widgets, auto_dismiss=auto_dismiss)
        fields = current_recovery_status()
    except Exception as exc:  # noqa: BLE001 — detector must never break tools
        logger.debug("Maya recovery-dialog poll skipped: %s", exc)
        return result

    if not fields or not isinstance(result, dict):
        return result

    out = dict(result)
    context = out.get("context")
    if not isinstance(context, dict):
        context = {}
    else:
        context = dict(context)
    context.update(fields)
    out["context"] = context
    return out


def current_context_fields() -> Dict[str, Any]:
    """Return fields safe to merge into a Maya context snapshot."""
    return current_recovery_status()


def reset_for_tests() -> None:
    """Reset module state for unit tests."""
    clear_recovery_status()


def _scan_recovery_dialog(
    qt_widgets: Optional[Any] = None,
    auto_dismiss: Optional[bool] = None,
) -> Dict[str, Any]:
    widgets_api = qt_widgets if qt_widgets is not None else _import_qt_widgets()
    if widgets_api is None:
        return _no_dialog_event()

    should_dismiss = resolve_auto_dismiss(auto_dismiss)
    for widget in _iter_top_level_widgets(widgets_api):
        if not _is_visible(widget):
            continue
        title = _call_text(widget, "windowTitle")
        if not _matches_recovery_title(title):
            continue

        dismissed = False
        dismissal_attempted = should_dismiss
        if should_dismiss:
            dismissed = _dismiss_widget(widget, widgets_api)

        status = _STATUS_RECOVERED if dismissed else _STATUS_DETECTED
        event = {
            "detected": True,
            "active": not dismissed,
            "dismissed": dismissed,
            "dismissal_attempted": dismissal_attempted,
            "status": status,
            "title": title,
            "source": "qt_top_level_window",
            "timestamp": time.time(),
        }
        logger.warning(
            "Detected Maya recovery dialog%s: %s",
            " and dismissed it" if dismissed else "",
            title,
        )
        return event

    return _mark_recovered_if_previous_dialog_cleared()


def _record_event(event: Dict[str, Any]) -> None:
    global _last_event
    with _state_lock:
        _last_event = copy.deepcopy(event)


def _no_dialog_event() -> Dict[str, Any]:
    return {
        "detected": False,
        "active": False,
        "dismissed": False,
        "dismissal_attempted": False,
        "status": "ok",
        "source": "qt_top_level_window",
        "timestamp": time.time(),
    }


def _mark_recovered_if_previous_dialog_cleared() -> Dict[str, Any]:
    with _state_lock:
        previous = copy.deepcopy(_last_event)
    if previous and previous.get("active"):
        previous["detected"] = False
        previous["active"] = False
        previous["dismissed"] = bool(previous.get("dismissed"))
        previous["status"] = _STATUS_RECOVERED
        previous["timestamp"] = time.time()
        return previous
    return _no_dialog_event()


def _import_qt_widgets() -> Optional[Any]:
    for module_name in ("PySide6.QtWidgets", "PySide2.QtWidgets", "PySide.QtGui"):
        try:
            module = __import__(module_name, fromlist=["dummy"])
            return module
        except Exception:  # noqa: BLE001
            continue
    return None


def _iter_top_level_widgets(qt_widgets: Any) -> Iterable[Any]:
    if isinstance(qt_widgets, (list, tuple)):
        return list(qt_widgets)

    app_cls = getattr(qt_widgets, "QApplication", None)
    if app_cls is None:
        return []

    widgets = _call(app_cls, "topLevelWidgets")
    if widgets is None:
        instance = _call(app_cls, "instance")
        widgets = _call(instance, "topLevelWidgets") if instance is not None else None
    if widgets is None:
        return []
    try:
        return list(widgets)
    except TypeError:
        return []


def _matches_recovery_title(title: str) -> bool:
    if not title:
        return False

    lower = title.strip().lower()
    if "stopped working" in lower or "has stopped working" in lower:
        return True
    if "recover" in lower and any(marker in lower for marker in ("maya", "file", "crash", "report")):
        return True
    if "crash" in lower and any(marker in lower for marker in ("maya", "report", "recovery")):
        return True

    return any(marker in title for marker in ("已停止工作", "正在恢复", "恢复文件"))


def _dismiss_widget(widget: Any, qt_widgets: Any) -> bool:
    for button in _iter_buttons(widget, qt_widgets):
        label = _call_text(button, "text").strip().lower()
        if not label or not any(marker in label for marker in _BUTTON_MARKERS):
            continue
        if _invoke(button, "click"):
            return True

    if _invoke(widget, "accept"):
        return True
    return _invoke(widget, "close")


def _iter_buttons(widget: Any, qt_widgets: Any) -> List[Any]:
    find_children = getattr(widget, "findChildren", None)
    if find_children is None:
        return []

    classes = []
    button_cls = getattr(qt_widgets, "QAbstractButton", None)
    if button_cls is not None:
        classes.append(button_cls)
    classes.append(object)

    seen = set()
    buttons: List[Any] = []
    for cls in classes:
        try:
            children = find_children(cls)
        except TypeError:
            try:
                children = find_children()
            except Exception:  # noqa: BLE001
                continue
        except Exception:  # noqa: BLE001
            continue
        for child in children or []:
            ident = id(child)
            if ident in seen:
                continue
            seen.add(ident)
            if hasattr(child, "text") and hasattr(child, "click"):
                buttons.append(child)
    return buttons


def _is_visible(widget: Any) -> bool:
    value = _call(widget, "isVisible")
    return True if value is None else bool(value)


def _call_text(obj: Any, method_name: str) -> str:
    value = _call(obj, method_name)
    return "" if value is None else str(value)


def _call(obj: Any, method_name: str, *args: Any) -> Any:
    if obj is None:
        return None
    method = getattr(obj, method_name, None)
    if method is None:
        return None
    try:
        return method(*args)
    except Exception:  # noqa: BLE001
        return None


def _invoke(obj: Any, method_name: str, *args: Any) -> bool:
    if obj is None:
        return False
    method = getattr(obj, method_name, None)
    if method is None:
        return False
    try:
        method(*args)
        return True
    except Exception:  # noqa: BLE001
        return False


__all__ = [
    "ENV_AUTO_DISMISS_CRASH_DIALOG",
    "clear_recovery_status",
    "current_context_fields",
    "current_recovery_status",
    "poll_and_annotate_result",
    "reset_for_tests",
    "resolve_auto_dismiss",
    "scan_recovery_dialog",
]
