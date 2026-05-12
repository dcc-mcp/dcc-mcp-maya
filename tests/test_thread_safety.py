"""Static guardrails for Maya API calls in worker-thread targets."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Optional

SRC = Path(__file__).resolve().parent.parent / "src" / "dcc_mcp_maya"
_EXCLUDED_PARTS = {"skills"}
_THREAD_TARGET_HINTS = ("_worker", "_async_worker", "_thread_body")
_FORBIDDEN_ROOTS = (
    ("cmds",),
    ("mel",),
    ("maya", "cmds"),
    ("maya", "mel"),
    ("maya", "OpenMaya"),
)
_ALLOWED_DECORATORS = {"require_main_thread", "dcc_mcp_maya.api.require_main_thread"}


def _iter_source_files() -> Iterable[Path]:
    for path in SRC.rglob("*.py"):
        if _EXCLUDED_PARTS.intersection(path.relative_to(SRC).parts):
            continue
        yield path


def _dotted_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _is_thread_target_use(node: ast.Call) -> Optional[str]:
    func_name = _dotted_name(node.func)
    if func_name not in {"Thread", "threading.Thread"}:
        return None
    for kw in node.keywords:
        if kw.arg == "target":
            return _dotted_name(kw.value)
    return None


def _has_allowed_guard(fn: ast.FunctionDef) -> bool:
    for decorator in fn.decorator_list:
        name = _dotted_name(decorator.func if isinstance(decorator, ast.Call) else decorator)
        if name in _ALLOWED_DECORATORS:
            return True
    return False


def _forbidden_call(node: ast.AST) -> Optional[ast.AST]:
    for child in ast.walk(node):
        if not isinstance(child, ast.Attribute):
            continue
        name = _dotted_name(child)
        if not name:
            continue
        parts = tuple(name.split("."))
        for root in _FORBIDDEN_ROOTS:
            if parts[: len(root)] == root and len(parts) > len(root):
                return child
    return None


def test_no_maya_api_calls_in_worker_thread_targets():
    failures = []
    for path in _iter_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        thread_targets = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                target = _is_thread_target_use(node)
                if target:
                    thread_targets.add(target.rsplit(".", 1)[-1])

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            is_worker = node.name in thread_targets or any(
                node.name.endswith(suffix) for suffix in _THREAD_TARGET_HINTS
            )
            if not is_worker or _has_allowed_guard(node):
                continue
            bad = _forbidden_call(node)
            if bad is not None:
                rel = path.relative_to(SRC.parent).as_posix()
                failures.append(
                    f"{rel}:{bad.lineno}: {node.name} runs on a worker thread but reaches Maya APIs; "
                    "marshal via MayaUiDispatcher.submit_callable(...) or add @require_main_thread."
                )

    assert not failures, "\n".join(failures)
