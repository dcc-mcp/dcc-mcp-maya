"""Regression for core#999 — MayaUiDispatcher honours timeout_hint_secs."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from dcc_mcp_maya.dispatcher.ui import MayaUiDispatcher


def test_dispatch_callable_forwards_timeout_hint_as_timeout_ms(monkeypatch) -> None:
    dispatcher = MayaUiDispatcher()
    captured: Dict[str, Any] = {}

    def _fake_submit(
        request_id: str,
        task: Callable[[], Any],
        affinity: str = "main",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        captured["timeout_ms"] = timeout_ms
        return {
            "request_id": request_id,
            "affinity": affinity,
            "success": True,
            "output": task(),
            "error": None,
        }

    monkeypatch.setattr(dispatcher, "submit_callable", _fake_submit)

    out = dispatcher.dispatch_callable(
        lambda: 42,
        timeout_hint_secs=120,
        thread_affinity="main",
        execution="async",
    )
    assert out == 42
    assert captured["timeout_ms"] == 120_000
