"""Tests for per-action thread-affinity resolution and executor routing.

Covers three layers:

1. :mod:`dcc_mcp_maya._affinity` — the pure ``tools.yaml`` loader
   (handles sibling-file layout, unknown values, missing files, cache
   invalidation, and injectable loaders for filesystem-free tests).
2. :mod:`dcc_mcp_maya._executor.execute_in_process` — the routing
   decision.  ``affinity: main`` must go through the Maya UI dispatcher
   while ``affinity: any`` must execute inline on the calling thread.
3. Bundled skills audit — confirms the production ``tools.yaml`` files
   still map to the affinities the runtime assumes.  This guards
   against silent regressions where a skill edit flips an action from
   ``any`` to ``main`` (or vice-versa) without updating the handler.

These tests never import ``maya.cmds``.  They exercise the real
executor code-path against an in-memory fake dispatcher so they run
in plain CPython under CI.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

# Import project modules
from dcc_mcp_maya import _affinity
from dcc_mcp_maya._executor import execute_in_process, run_skill_script

REPO_SRC = Path(__file__).resolve().parent.parent / "src" / "dcc_mcp_maya"
BUNDLED_SKILLS = REPO_SRC / "skills"

# ---------------------------------------------------------------------------
# _affinity — parser / cache layer
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_affinity_cache():
    """Start every test with a fresh cache to avoid cross-test bleed."""
    _affinity.clear_cache()
    yield
    _affinity.clear_cache()


def _write_skill(tmp_path: Path, tools_yaml_body: str, script_name: str = "do_thing.py") -> Path:
    """Materialise a minimal ``<skill>/tools.yaml`` + ``scripts/<name>`` layout."""
    skill_root = tmp_path / "skill-under-test"
    (skill_root / "scripts").mkdir(parents=True)
    (skill_root / "tools.yaml").write_text(tools_yaml_body, encoding="utf-8")
    script = skill_root / "scripts" / script_name
    script.write_text("def main(**_):\n    return {'success': True, 'message': 'ok'}\n", encoding="utf-8")
    return script


def test_resolve_returns_any_when_declared(tmp_path: Path):
    """``affinity: any`` in tools.yaml must flow through to the resolver."""
    script = _write_skill(
        tmp_path,
        "tools:\n- name: do_thing\n  execution: sync\n  affinity: any\n",
    )
    assert _affinity.resolve_affinity(str(script)) == "any"


def test_resolve_returns_main_when_declared(tmp_path: Path):
    """``affinity: main`` in tools.yaml maps to ``main``."""
    script = _write_skill(
        tmp_path,
        "tools:\n- name: do_thing\n  execution: sync\n  affinity: main\n",
    )
    assert _affinity.resolve_affinity(str(script)) == "main"


def test_resolve_defaults_to_main_on_missing_tools_yaml(tmp_path: Path):
    """Missing ``tools.yaml`` → safe default (``main``), never raises."""
    skill_root = tmp_path / "legacy-skill"
    (skill_root / "scripts").mkdir(parents=True)
    script = skill_root / "scripts" / "legacy.py"
    script.write_text("def main(**_):\n    return {'success': True}\n", encoding="utf-8")
    assert _affinity.resolve_affinity(str(script)) == "main"


def test_resolve_defaults_to_main_on_missing_entry(tmp_path: Path):
    """Script present but not declared in tools.yaml → default (main)."""
    script = _write_skill(
        tmp_path,
        "tools:\n- name: something_else\n  execution: sync\n  affinity: any\n",
    )
    assert _affinity.resolve_affinity(str(script)) == "main"


def test_resolve_defaults_to_main_on_unknown_affinity_value(tmp_path: Path):
    """Malformed affinity value must degrade to the default."""
    script = _write_skill(
        tmp_path,
        "tools:\n- name: do_thing\n  execution: sync\n  affinity: teleport\n",
    )
    assert _affinity.resolve_affinity(str(script)) == "main"


def test_resolve_defaults_to_main_on_missing_source_file():
    """None or empty source_file → default (main)."""
    assert _affinity.resolve_affinity(None) == "main"
    assert _affinity.resolve_affinity("") == "main"


def test_resolve_rejects_non_scripts_layout(tmp_path: Path):
    """Scripts not under ``<skill>/scripts/`` → default (main).

    We refuse to guess at unconventional layouts because guessing wrong
    (crashing Maya) is strictly worse than missing the optimisation.
    """
    skill_root = tmp_path / "weird-layout"
    skill_root.mkdir()
    (skill_root / "tools.yaml").write_text(
        "tools:\n- name: do_thing\n  execution: sync\n  affinity: any\n",
        encoding="utf-8",
    )
    # Script lives at the skill root, not under scripts/
    script = skill_root / "do_thing.py"
    script.write_text("", encoding="utf-8")
    assert _affinity.resolve_affinity(str(script)) == "main"


def test_resolve_caches_result(tmp_path: Path):
    """Second call for the same path must not re-parse ``tools.yaml``."""
    script = _write_skill(
        tmp_path,
        "tools:\n- name: do_thing\n  execution: sync\n  affinity: any\n",
    )
    first = _affinity.resolve_affinity(str(script))
    # Corrupt the YAML — the cache must shield us from re-reading it.
    (script.parent.parent / "tools.yaml").write_text("{{{not-yaml", encoding="utf-8")
    second = _affinity.resolve_affinity(str(script))
    assert first == second == "any"


def test_resolve_honours_injected_loader(tmp_path: Path):
    """A custom loader lets tests avoid filesystem I/O entirely."""
    script = _write_skill(
        tmp_path,
        "tools:\n- name: do_thing\n  execution: sync\n  affinity: main\n",
    )

    captured: List[str] = []

    def fake_loader(skill_root: str) -> Dict[str, Any]:
        captured.append(skill_root)
        return {"tools": [{"name": "do_thing", "affinity": "any"}]}

    # The injected loader overrides the on-disk YAML entirely.
    resolved = _affinity.resolve_affinity(str(script), loader=fake_loader)
    assert resolved == "any"
    # The loader must receive the skill root (parent of scripts/).
    assert captured and captured[0].endswith("skill-under-test")


def test_resolve_is_thread_safe(tmp_path: Path):
    """Concurrent callers must not corrupt the cache."""
    scripts = []
    for idx in range(8):
        script = _write_skill(
            tmp_path / str(idx),
            "tools:\n- name: do_thing\n  execution: sync\n  affinity: {}\n".format("any" if idx % 2 == 0 else "main"),
        )
        scripts.append(str(script))

    results: Dict[int, str] = {}

    def worker(i: int) -> None:
        results[i] = _affinity.resolve_affinity(scripts[i])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(scripts))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    for idx, scr in enumerate(scripts):
        expected = "any" if idx % 2 == 0 else "main"
        assert results[idx] == expected, "Unexpected resolution for {}".format(scr)


# ---------------------------------------------------------------------------
# _executor.execute_in_process — routing layer
# ---------------------------------------------------------------------------


class _RecordingDispatcher:
    """Fake dispatcher that records calls and returns a canned result.

    Returns the ``{"success": bool, "output": <inner>}`` envelope shape
    produced by the real :class:`MayaUiDispatcher` so the executor's
    result-unwrapping logic exercises the same code path as production.
    """

    def __init__(self, result: Optional[dict] = None):
        self.calls: List[Dict[str, Any]] = []
        self._override = result

    def submit_callable(self, action_name: str, fn: Callable[[], Any], *, affinity: str = "main") -> Any:
        self.calls.append({"action": action_name, "affinity": affinity})
        if self._override is not None:
            return self._override
        # Drive the wrapped callable (so side-effects in the skill still
        # run) and wrap its output in the dispatcher envelope shape.
        inner = fn()
        return {"success": True, "output": inner}


class _FakeServer:
    def __init__(self, dispatcher: Optional[Any]):
        self._maya_dispatcher = dispatcher


@pytest.fixture
def any_affinity_script(tmp_path: Path) -> str:
    return str(
        _write_skill(
            tmp_path,
            "tools:\n- name: do_thing\n  execution: sync\n  affinity: any\n",
        )
    )


@pytest.fixture
def main_affinity_script(tmp_path: Path) -> str:
    return str(
        _write_skill(
            tmp_path,
            "tools:\n- name: do_thing\n  execution: sync\n  affinity: main\n",
        )
    )


def test_executor_bypasses_dispatcher_for_any_affinity(any_affinity_script: str):
    """``affinity: any`` must execute inline, not touch the dispatcher.

    This is the core of the token / latency optimisation: a filesystem
    lookup should never compete with Maya's UI thread queue.
    """
    dispatcher = _RecordingDispatcher()
    server = _FakeServer(dispatcher)

    result = execute_in_process(server, any_affinity_script, {}, "skill__do_thing")

    assert result == {"success": True, "message": "ok"}
    assert dispatcher.calls == [], "dispatcher must NOT be invoked for affinity: any"


def test_executor_routes_main_affinity_through_dispatcher(main_affinity_script: str, monkeypatch):
    """``affinity: main`` must go through the UI dispatcher when off main thread.

    The off-main-thread simulation is required because pytest runs on the
    Python main thread; calling ``submit_callable`` from the main thread
    would deadlock waiting for itself — guarded by the
    ``_on_main_thread()`` short-circuit in ``execute_in_process``.
    """
    from dcc_mcp_maya import _executor as _executor_mod

    monkeypatch.setattr(_executor_mod, "_on_main_thread", lambda: False)

    dispatcher = _RecordingDispatcher()
    server = _FakeServer(dispatcher)

    result = execute_in_process(server, main_affinity_script, {}, "skill__do_thing")

    assert result == {"success": True, "message": "ok"}
    assert len(dispatcher.calls) == 1
    assert dispatcher.calls[0]["action"] == "skill__do_thing"
    assert dispatcher.calls[0]["affinity"] == "main"


def test_executor_falls_back_to_inline_without_dispatcher(main_affinity_script: str):
    """Standalone / mayapy mode has no dispatcher — must still work."""
    server = _FakeServer(None)
    result = execute_in_process(server, main_affinity_script, {}, "skill__do_thing")
    assert result == {"success": True, "message": "ok"}


def test_executor_surfaces_dispatcher_exceptions_as_envelope(main_affinity_script: str, monkeypatch):
    """When the dispatcher raises, the caller sees a structured envelope,
    never an uncaught exception (keeps MCP response contract intact)."""
    # Pretend we are on a tokio worker thread so the executor actually
    # consults the dispatcher; otherwise ``_on_main_thread()=True`` would
    # short-circuit to inline execution (the correct production guard
    # against deadlocking ``submit_callable`` against itself).
    from dcc_mcp_maya import _executor as _executor_mod

    monkeypatch.setattr(_executor_mod, "_on_main_thread", lambda: False)

    class _BrokenDispatcher:
        def submit_callable(self, action_name, fn, *, affinity="main"):
            raise RuntimeError("main thread is on fire")

    server = _FakeServer(_BrokenDispatcher())
    result = execute_in_process(server, main_affinity_script, {}, "skill__do_thing")
    assert isinstance(result, dict)
    assert result.get("success") is False
    message = result.get("message") or result.get("error") or ""
    assert "main thread is on fire" in str(message) or "Dispatcher" in str(message)


def test_run_skill_script_returns_structured_error_on_missing_script(tmp_path: Path):
    """Defensive: missing script must not crash the executor."""
    result = run_skill_script(str(tmp_path / "does_not_exist.py"), {})
    assert result["success"] is False
    assert "Cannot load" in result["message"] or "Error loading" in result["message"]


# ---------------------------------------------------------------------------
# Bundled skills — audit contract (real skills.yaml files)
# ---------------------------------------------------------------------------


def test_bundled_render_farm_get_job_status_is_affinity_any():
    """``maya-render-farm/get_render_job_status`` is pure subprocess I/O.

    Sanity-check the bundled declaration so a future skill edit that
    re-routes it to the main thread fails this test instead of silently
    regressing the fix.
    """
    script = BUNDLED_SKILLS / "maya-render-farm" / "scripts" / "get_render_job_status.py"
    assert script.is_file(), "bundled render-farm skill missing"
    assert _affinity.resolve_affinity(str(script)) == "any"


def test_bundled_execute_python_is_affinity_main():
    """``maya-scripting/execute_python`` runs arbitrary user code and MUST
    stay on the Maya UI thread.  This is a critical safety invariant."""
    script = BUNDLED_SKILLS / "maya-scripting" / "scripts" / "execute_python.py"
    assert script.is_file(), "bundled scripting skill missing"
    assert _affinity.resolve_affinity(str(script)) == "main"


def test_bundled_scene_family_is_affinity_main():
    """Every scene-management action must declare ``main``."""
    scene_scripts = (BUNDLED_SKILLS / "maya-scene" / "scripts").glob("*.py")
    script_list = list(scene_scripts)
    assert script_list, "maya-scene skill missing"
    for script in script_list:
        assert _affinity.resolve_affinity(str(script)) == "main", "{} must declare affinity: main in tools.yaml".format(
            script.name
        )
