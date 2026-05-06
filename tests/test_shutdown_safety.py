"""Unit tests for the shutdown safety nets (issue #186).

Covers the four independent nets that make non-cooperative Maya exits
stop leaking FileRegistry rows:

1. ``MSceneMessage.kMayaExiting`` hook — registration + callback invocation.
2. ``atexit`` fallback — hook registration + unregistration.
3. Crash-resilient process sentinel — filesystem marker that disappears
   when the process dies.
4. Defensive ``__del__`` guard — opt-in safety belt for interpreter
   teardown cases where nobody called ``stop_server()``.

Plus the :class:`ShutdownCoordinator` that composes them together.

The ``kMayaExiting`` case fakes ``maya.api.OpenMaya`` via
``sys.modules`` so the real Maya is not required — the same pattern
used by ``tests/test_dispatcher.py::mock_maya_modules``.  The
``atexit`` case also gets a subprocess test that proves the hook
actually fires during real interpreter teardown.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import threading
from pathlib import Path
from typing import Any, Callable, List
from unittest.mock import MagicMock, patch

import pytest

from dcc_mcp_maya import (
    ENV_ATEXIT_HOOK,
    ENV_DEFENSIVE_DEL,
    ENV_KMAYA_EXITING_HOOK,
    ENV_PROCESS_SENTINEL,
    DefensiveShutdownGuard,
    ShutdownCoordinator,
    orphan_sentinels,
    register_atexit_hook,
    register_kmaya_exiting_hook,
    sentinel_path,
    unregister_atexit_hook,
    unregister_kmaya_exiting_hook,
    write_process_sentinel,
)
from dcc_mcp_maya._shutdown_safety import _env_enabled

# ---------------------------------------------------------------------------
# _env_enabled — the tiny switch helper
# ---------------------------------------------------------------------------


class TestEnvEnabled:
    def test_unset_returns_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SAFETY_TEST_VAR", raising=False)
        assert _env_enabled("SAFETY_TEST_VAR", default=True) is True
        assert _env_enabled("SAFETY_TEST_VAR", default=False) is False

    @pytest.mark.parametrize(
        "val,expected",
        [
            ("1", True),
            ("true", True),
            ("TRUE", True),
            ("Yes", True),
            ("on", True),
            ("0", False),
            ("false", False),
            ("off", False),
            ("no", False),
        ],
    )
    def test_canonical_tokens(
        self,
        monkeypatch: pytest.MonkeyPatch,
        val: str,
        expected: bool,
    ) -> None:
        monkeypatch.setenv("SAFETY_TEST_VAR", val)
        # ``default`` is deliberately opposite to ``expected`` so the
        # test fails if the function silently falls back.
        assert _env_enabled("SAFETY_TEST_VAR", default=not expected) is expected

    def test_unknown_value_collapses_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SAFETY_TEST_VAR", "maybe")
        assert _env_enabled("SAFETY_TEST_VAR", default=True) is True
        assert _env_enabled("SAFETY_TEST_VAR", default=False) is False


# ---------------------------------------------------------------------------
# kMayaExiting hook — fake MSceneMessage via sys.modules patch
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_open_maya() -> Any:
    """Inject a stub ``maya.api.OpenMaya`` with a working ``MSceneMessage``."""
    fake = MagicMock()
    fake.MSceneMessage = MagicMock()
    fake.MSceneMessage.kMayaExiting = 41  # arbitrary Maya constant
    # ``addCallback`` returns a fresh integer id each call; sweeper tests
    # assert on the id to confirm round-trip correctness.
    counter = {"n": 1000}

    def _add_callback(_event: int, cb: Callable[[Any], None]) -> int:
        counter["n"] += 1
        fake.MSceneMessage.last_callback = cb
        return counter["n"]

    fake.MSceneMessage.addCallback.side_effect = _add_callback
    fake.MSceneMessage.removeCallback = MagicMock()

    modules = {
        "maya": MagicMock(),
        "maya.api": MagicMock(),
        "maya.api.OpenMaya": fake,
    }
    modules["maya"].api = modules["maya.api"]
    modules["maya.api"].OpenMaya = fake
    with patch.dict(sys.modules, modules):
        yield fake


class TestKMayaExitingHook:
    def test_register_returns_callback_id(self, fake_open_maya: Any) -> None:
        def _callback() -> None:
            pass

        cb_id = register_kmaya_exiting_hook(_callback)
        assert cb_id is not None
        assert cb_id > 1000  # our fake counter started at 1000
        fake_open_maya.MSceneMessage.addCallback.assert_called_once()

    def test_registered_callback_is_guarded(self, fake_open_maya: Any) -> None:
        """User callback exceptions must never escape to Maya's event loop."""
        called: List[str] = []

        def _raising_callback() -> None:
            called.append("ran")
            raise RuntimeError("boom")

        register_kmaya_exiting_hook(_raising_callback)
        wrapped = fake_open_maya.MSceneMessage.last_callback
        # Invoke the guarded wrapper directly — exception must NOT escape.
        wrapped({"client_data": None})
        assert called == ["ran"]

    def test_register_returns_none_when_openmaya_missing(self) -> None:
        """Non-Maya Python must degrade gracefully."""
        # sys.modules has no ``maya.api.OpenMaya`` in this fixture-less test.
        assert register_kmaya_exiting_hook(lambda: None) is None

    def test_unregister_success(self, fake_open_maya: Any) -> None:
        cb_id = register_kmaya_exiting_hook(lambda: None)
        assert unregister_kmaya_exiting_hook(cb_id) is True
        fake_open_maya.MSceneMessage.removeCallback.assert_called_once_with(cb_id)

    def test_unregister_ignores_none(self) -> None:
        assert unregister_kmaya_exiting_hook(None) is False


# ---------------------------------------------------------------------------
# atexit fallback
# ---------------------------------------------------------------------------


class TestAtExitHook:
    def test_register_returns_hook(self) -> None:
        hook = register_atexit_hook(lambda: None)
        try:
            assert callable(hook)
        finally:
            unregister_atexit_hook(hook)

    def test_idempotent_via_guard(self) -> None:
        calls: List[int] = []
        hook = register_atexit_hook(lambda: calls.append(1))
        try:
            hook()
            hook()  # Second call should no-op.
            assert calls == [1]
        finally:
            unregister_atexit_hook(hook)

    def test_hook_catches_exceptions(self) -> None:
        """A failing callback must not propagate — interpreter teardown is sensitive."""

        def _boom() -> None:
            raise RuntimeError("shutdown error")

        hook = register_atexit_hook(_boom)
        try:
            hook()  # must not raise
        finally:
            unregister_atexit_hook(hook)

    def test_unregister_hook(self) -> None:
        hook = register_atexit_hook(lambda: None)
        assert unregister_atexit_hook(hook) is True
        assert unregister_atexit_hook(None) is False

    def test_atexit_fires_in_subprocess(self, tmp_path: Path) -> None:
        """End-to-end proof that the hook actually fires on interpreter exit."""
        marker = tmp_path / "atexit_fired.marker"
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(Path("src").resolve())!r})
            from dcc_mcp_maya._shutdown_safety import register_atexit_hook
            def _on_exit() -> None:
                open({str(marker)!r}, "w").write("fired")
            register_atexit_hook(_on_exit)
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert marker.is_file()
        assert marker.read_text() == "fired"


# ---------------------------------------------------------------------------
# Process sentinel
# ---------------------------------------------------------------------------


class TestProcessSentinel:
    def test_sentinel_path_encodes_pid_and_id(self, tmp_path: Path) -> None:
        path = sentinel_path("maya-abc", registry_dir=str(tmp_path))
        assert str(os.getpid()) in path.name
        assert "maya-abc" in path.name
        assert path.suffix == ".sentinel"
        assert str(tmp_path) in str(path)

    def test_sentinel_path_sanitises_instance_id(self, tmp_path: Path) -> None:
        path = sentinel_path("bad/name with:chars", registry_dir=str(tmp_path))
        # Only alphanumerics / - / _ survive.
        assert "/" not in path.name
        assert ":" not in path.name

    def test_open_creates_file_and_writes_pid(self, tmp_path: Path) -> None:
        sentinel = write_process_sentinel("test", registry_dir=str(tmp_path))
        assert sentinel is not None
        try:
            assert sentinel.path.is_file()
            assert sentinel.is_alive()
            content = sentinel.path.read_text().strip() if sys.platform != "win32" else None
            if content is not None:
                # On Windows O_TEMPORARY prevents other handles from reading
                # while open; only assert on POSIX where content is visible.
                assert str(os.getpid()) in content
        finally:
            sentinel.cleanup()
        # After cleanup the file must be gone and the handle released.
        assert not sentinel.path.exists()
        assert sentinel.is_alive() is False

    def test_cleanup_is_idempotent(self, tmp_path: Path) -> None:
        sentinel = write_process_sentinel("test", registry_dir=str(tmp_path))
        assert sentinel is not None
        sentinel.cleanup()
        sentinel.cleanup()  # second call must not raise
        assert not sentinel.path.exists()

    def test_write_returns_none_when_dir_unwritable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Graceful degradation when we cannot open the marker."""

        def _fail(*_args: Any, **_kwargs: Any) -> int:
            raise OSError("disk full")

        monkeypatch.setattr(os, "open", _fail)
        assert write_process_sentinel("x", registry_dir=str(tmp_path)) is None

    def test_orphan_sentinels_reports_dead_pids(self, tmp_path: Path) -> None:
        # Write a sentinel with a PID that is guaranteed not to exist.
        bogus = 2**31 - 1  # highest int32 — essentially never allocated.
        subdir = tmp_path / "dcc-mcp-registry" / "sentinels"
        subdir.mkdir(parents=True)
        fake_sentinel = subdir / f"{bogus}-deadbeef.sentinel"
        fake_sentinel.write_text(f"{bogus}\n")

        orphans = orphan_sentinels(registry_dir=str(tmp_path))
        assert fake_sentinel in orphans

    def test_orphan_sentinels_ignores_live_pid(self, tmp_path: Path) -> None:
        sentinel = write_process_sentinel("live", registry_dir=str(tmp_path))
        assert sentinel is not None
        try:
            # On POSIX the file is readable on disk; on Windows with
            # O_TEMPORARY it may not appear in iterdir while open.  So
            # we only assert that the live PID is never in the orphan
            # list.
            orphans = orphan_sentinels(registry_dir=str(tmp_path))
            for path in orphans:
                assert not path.name.startswith(f"{os.getpid()}-")
        finally:
            sentinel.cleanup()


# ---------------------------------------------------------------------------
# DefensiveShutdownGuard
# ---------------------------------------------------------------------------


class TestDefensiveShutdownGuard:
    def test_disarm_prevents_callback(self) -> None:
        calls: List[int] = []
        guard = DefensiveShutdownGuard(lambda: calls.append(1))
        guard.disarm()
        del guard
        import gc

        gc.collect()
        assert calls == []

    def test_double_disarm_is_safe(self) -> None:
        guard = DefensiveShutdownGuard(lambda: None)
        guard.disarm()
        guard.disarm()  # must not raise


# ---------------------------------------------------------------------------
# ShutdownCoordinator — orchestration
# ---------------------------------------------------------------------------


class TestShutdownCoordinator:
    def test_install_and_uninstall_without_maya(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default path: kMayaExiting degrades, sentinel + atexit still wire."""
        monkeypatch.delenv(ENV_KMAYA_EXITING_HOOK, raising=False)
        monkeypatch.delenv(ENV_ATEXIT_HOOK, raising=False)
        monkeypatch.delenv(ENV_PROCESS_SENTINEL, raising=False)
        monkeypatch.delenv(ENV_DEFENSIVE_DEL, raising=False)

        calls: List[str] = []
        coord = ShutdownCoordinator()
        coord.install(
            lambda: calls.append("stopped"),
            instance_id="test",
            registry_dir=str(tmp_path),
        )
        assert coord.stop_already_ran is False
        coord.uninstall()  # must not raise even when kMayaExiting was not wired

    def test_install_is_idempotent(self, tmp_path: Path) -> None:
        coord = ShutdownCoordinator()
        coord.install(lambda: None, instance_id="x", registry_dir=str(tmp_path))
        coord.install(lambda: None, instance_id="x", registry_dir=str(tmp_path))
        coord.uninstall()

    def test_uninstall_without_install_is_safe(self) -> None:
        ShutdownCoordinator().uninstall()  # no-op

    def test_callback_runs_at_most_once(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Race between kMayaExiting and atexit must still deliver a single stop."""
        monkeypatch.setenv(ENV_KMAYA_EXITING_HOOK, "0")  # skip Maya
        monkeypatch.setenv(ENV_DEFENSIVE_DEL, "0")

        calls: List[int] = []
        coord = ShutdownCoordinator()
        coord.install(
            lambda: calls.append(1),
            instance_id="race-test",
            registry_dir=str(tmp_path),
        )
        guarded = coord._make_guarded_stop()  # type: ignore[attr-defined]
        # Simulate concurrent invocation from two safety nets:
        threads = [threading.Thread(target=guarded) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert calls == [1]
        assert coord.stop_already_ran is True
        coord.uninstall()

    def test_env_var_disables_sentinel(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_PROCESS_SENTINEL, "0")
        coord = ShutdownCoordinator()
        coord.install(
            lambda: None,
            instance_id="disable-test",
            registry_dir=str(tmp_path),
        )
        try:
            # No sentinel file should exist under the temp dir.
            sentinels_dir = tmp_path / "dcc-mcp-registry" / "sentinels"
            if sentinels_dir.exists():
                assert list(sentinels_dir.iterdir()) == []
        finally:
            coord.uninstall()

    def test_env_var_disables_atexit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_ATEXIT_HOOK, "0")
        coord = ShutdownCoordinator()
        coord.install(
            lambda: None,
            instance_id="atexit-off",
            registry_dir=str(tmp_path),
        )
        assert coord._atexit_hook is None  # type: ignore[attr-defined]
        coord.uninstall()

    def test_defensive_del_is_opt_in(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Unset — guard should not be built.
        monkeypatch.delenv(ENV_DEFENSIVE_DEL, raising=False)
        coord = ShutdownCoordinator()
        coord.install(lambda: None, instance_id="x", registry_dir=str(tmp_path))
        assert coord._guard is None  # type: ignore[attr-defined]
        coord.uninstall()

        # Opt in — guard is built.
        monkeypatch.setenv(ENV_DEFENSIVE_DEL, "1")
        coord2 = ShutdownCoordinator()
        coord2.install(lambda: None, instance_id="x", registry_dir=str(tmp_path))
        assert coord2._guard is not None  # type: ignore[attr-defined]
        coord2.uninstall()

    def test_coordinator_calls_kmaya_hook_when_triggered(
        self,
        fake_open_maya: Any,
        tmp_path: Path,
    ) -> None:
        """End-to-end: simulate Maya firing kMayaExiting → stop callback runs."""
        calls: List[str] = []
        coord = ShutdownCoordinator()
        coord.install(
            lambda: calls.append("stopped"),
            instance_id="kmaya-test",
            registry_dir=str(tmp_path),
        )
        try:
            # Our fake MSceneMessage stashed the wrapped callback.
            wrapped = fake_open_maya.MSceneMessage.last_callback
            assert wrapped is not None
            wrapped({"client_data": None})
            assert calls == ["stopped"]
            assert coord.stop_already_ran is True
        finally:
            coord.uninstall()


# ---------------------------------------------------------------------------
# Crash-smoke test — proves the sentinel actually drops on os._exit
# ---------------------------------------------------------------------------


class TestCrashResilientSentinel:
    """End-to-end proof that a process-crash drops the sentinel marker.

    Launches a subprocess that opens a :class:`ProcessSentinel` and then
    exits hard via :func:`os._exit`.  After the subprocess dies we
    assert — from the parent — that the sentinel file is either already
    gone (Windows, via ``O_TEMPORARY``) or detectable as an orphan by
    :func:`orphan_sentinels` on POSIX.  This is the Maya-adapter-side
    complement to the issue's ``mayapy`` crash smoke test; a full
    integration test would boot ``mayapy`` itself but that is deferred
    to the existing ``tests/e2e`` suite.
    """

    def test_os_exit_drops_sentinel(self, tmp_path: Path) -> None:
        script = textwrap.dedent(
            f"""
            import os, sys, time
            sys.path.insert(0, {str(Path("src").resolve())!r})
            from dcc_mcp_maya._shutdown_safety import write_process_sentinel
            sentinel = write_process_sentinel(
                "crash-test",
                registry_dir={str(tmp_path)!r},
            )
            assert sentinel is not None
            # Print the PID so the parent can verify orphan detection.
            print(os.getpid(), flush=True)
            # Give the parent a moment to observe the file, then crash.
            time.sleep(0.2)
            os._exit(137)  # simulate kill -9 / Task Manager End Task
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # ``os._exit(137)`` skips atexit → the Python-side cleanup never
        # ran.  Only the OS-level ``O_TEMPORARY`` / sweeper path can
        # detect the dead process.
        assert result.returncode == 137
        dead_pid = int(result.stdout.strip().splitlines()[-1])

        sentinels_dir = tmp_path / "dcc-mcp-registry" / "sentinels"
        if sys.platform == "win32":
            # ``FILE_FLAG_DELETE_ON_CLOSE`` should have dropped the file
            # the moment the process died.  The directory may still
            # exist but no matching sentinel should survive.
            survivors = list(sentinels_dir.iterdir()) if sentinels_dir.is_dir() else []
            for entry in survivors:
                assert not entry.name.startswith(f"{dead_pid}-")
        else:
            # On POSIX the marker is still on disk but orphan_sentinels
            # must flag it as dead (matching PID is not alive).
            orphans = orphan_sentinels(registry_dir=str(tmp_path))
            dead_names = [p.name for p in orphans]
            assert any(name.startswith(f"{dead_pid}-") for name in dead_names), (
                f"expected an orphan for dead pid {dead_pid}, got {dead_names}"
            )
