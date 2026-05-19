"""Scoped guard for Maya ``cmds.file`` calls that would open modal prompts."""

from __future__ import annotations

import contextlib
from typing import Any, Callable, Iterator, Optional


class MayaFilePromptBlockedError(RuntimeError):
    """Raised when an MCP-dispatched ``cmds.file`` call would prompt."""


def _truthy(kwargs: dict, *names: str) -> bool:
    return any(bool(kwargs.get(name)) for name in names)


def _has_any(kwargs: dict, *names: str) -> bool:
    return any(name in kwargs for name in names)


def _query_bool(file_fn: Callable[..., Any], *names: str) -> bool:
    for name in names:
        try:
            return bool(file_fn(query=True, **{name: True}))
        except TypeError:
            try:
                return bool(file_fn(q=True, **{name: True}))
            except Exception:
                continue
        except Exception:
            continue
    return False


def _scene_path(file_fn: Callable[..., Any]) -> str:
    for key in ("sceneName", "sn"):
        try:
            return str(file_fn(query=True, **{key: True}) or "")
        except TypeError:
            try:
                return str(file_fn(q=True, **{key: True}) or "")
            except Exception:
                continue
        except Exception:
            continue
    return ""


def _scene_modified(file_fn: Callable[..., Any]) -> bool:
    return _query_bool(file_fn, "modified", "mf")


def _is_query(kwargs: dict) -> bool:
    return _truthy(kwargs, "query", "q")


def _has_force(kwargs: dict) -> bool:
    return _has_any(kwargs, "force", "f")


def _is_new_or_open(kwargs: dict) -> bool:
    return _truthy(kwargs, "new", "open", "o")


def _is_import_or_reference(kwargs: dict) -> bool:
    return _truthy(kwargs, "i", "import", "reference", "r") or _has_any(
        kwargs,
        "loadReference",
        "lr",
        "removeReference",
        "rr",
        "unloadReference",
        "ur",
    )


def _guarded_file_call(file_fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    if _is_query(kwargs):
        return file_fn(*args, **kwargs)

    if _is_new_or_open(kwargs) and not _has_force(kwargs):
        if _scene_modified(file_fn):
            action = "new" if _truthy(kwargs, "new") else "open"
            raise MayaFilePromptBlockedError(
                "Blocked cmds.file({}=True) because the current scene has unsaved changes and force=True was not "
                "provided. Save first or pass force=True to discard changes.".format(action)
            )
        kwargs["force"] = True

    if _is_import_or_reference(kwargs) and "prompt" not in kwargs:
        kwargs["prompt"] = False

    if _truthy(kwargs, "save", "s") and not _scene_path(file_fn):
        raise MayaFilePromptBlockedError(
            "Blocked cmds.file(save=True) on an unnamed scene because Maya would prompt for a file path. "
            "Call save_scene(file_path=...) or cmds.file(rename=...) first."
        )

    return file_fn(*args, **kwargs)


@contextlib.contextmanager
def guard_cmds_file(cmds_module: Optional[Any] = None) -> Iterator[None]:
    """Temporarily wrap ``maya.cmds.file`` with MCP-safe prompt checks.

    This intentionally does not resurrect the retired ``mcp_safe_session`` dialog
    monkey-patch. Only ``cmds.file`` is wrapped, only for the current execution
    window, and the original callable is restored even when the script fails.
    """
    if cmds_module is None:
        try:
            import maya.cmds as cmds_module  # type: ignore[no-redef]  # noqa: PLC0415
        except Exception:
            yield
            return

    original = getattr(cmds_module, "file", None)
    if original is None or getattr(original, "_dcc_mcp_file_guard", False):
        yield
        return

    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        return _guarded_file_call(original, *args, **kwargs)

    _wrapped._dcc_mcp_file_guard = True  # type: ignore[attr-defined]
    cmds_module.file = _wrapped
    try:
        yield
    finally:
        cmds_module.file = original
