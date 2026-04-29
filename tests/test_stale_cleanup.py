"""Tests for ``dcc_mcp_maya._stale_cleanup`` (issue #126).

Validates the host-side stale FileRegistry detection and warning helper.

See: https://github.com/loonghao/dcc-mcp-maya/issues/126
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
from pathlib import Path
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya import _stale_cleanup


@pytest.fixture()
def registry(tmp_path: Path) -> Path:
    """Return a writable registry path inside ``tmp_path``."""
    target = tmp_path / _stale_cleanup.REGISTRY_SUBDIR / _stale_cleanup.REGISTRY_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _write_entries(path: Path, entries):
    path.write_text(json.dumps(entries), encoding="utf-8")


class TestRegistryPath:
    """``registry_path`` resolution."""

    def test_explicit_dir_takes_precedence(self, tmp_path):
        result = _stale_cleanup.registry_path(str(tmp_path))
        assert result == tmp_path / _stale_cleanup.REGISTRY_SUBDIR / _stale_cleanup.REGISTRY_FILE

    def test_env_var_used_when_no_arg(self, tmp_path):
        with patch.dict(os.environ, {"DCC_MCP_REGISTRY_DIR": str(tmp_path)}):
            result = _stale_cleanup.registry_path()
            assert result.parent.parent == tmp_path

    def test_falls_back_to_tempdir(self):
        env = os.environ.copy()
        env.pop("DCC_MCP_REGISTRY_DIR", None)
        with patch.dict(os.environ, env, clear=True):
            result = _stale_cleanup.registry_path()
            assert result.name == _stale_cleanup.REGISTRY_FILE
            assert result.parent.name == _stale_cleanup.REGISTRY_SUBDIR


class TestPidAlive:
    """``_pid_alive`` cross-platform liveness check."""

    def test_current_pid_is_alive(self):
        assert _stale_cleanup._pid_alive(os.getpid()) is True

    def test_invalid_pid_is_dead(self):
        assert _stale_cleanup._pid_alive(0) is False
        assert _stale_cleanup._pid_alive(-1) is False

    def test_definitely_dead_pid(self):
        # 2**31 - 2 — far above any realistic PID; must report dead.
        assert _stale_cleanup._pid_alive(2**31 - 2) is False


class TestCountStaleEntries:
    """``count_stale_entries`` reads JSON registry without mutating it."""

    def test_missing_file_returns_zero(self, tmp_path):
        alive, stale = _stale_cleanup.count_stale_entries(str(tmp_path))
        assert (alive, stale) == (0, 0)

    def test_unparseable_file_returns_zero(self, registry):
        registry.write_text("{not-json", encoding="utf-8")
        alive, stale = _stale_cleanup.count_stale_entries(str(registry.parent.parent))
        assert (alive, stale) == (0, 0)

    def test_non_list_payload_returns_zero(self, registry):
        registry.write_text(json.dumps({"oops": True}), encoding="utf-8")
        alive, stale = _stale_cleanup.count_stale_entries(str(registry.parent.parent))
        assert (alive, stale) == (0, 0)

    def test_mixed_alive_and_stale(self, registry):
        _write_entries(
            registry,
            [
                {"pid": os.getpid()},  # alive
                {"pid": 2**31 - 2},  # stale
                {"pid": 2**31 - 3},  # stale
                {"pid": "not-an-int"},  # ignored
                {"no_pid_at_all": True},  # ignored
                "not a dict",  # ignored
            ],
        )
        with patch.object(_stale_cleanup, "_pid_alive", side_effect=lambda p: p == os.getpid()):
            alive, stale = _stale_cleanup.count_stale_entries(str(registry.parent.parent))
        assert alive == 1
        assert stale == 2

    def test_empty_list(self, registry):
        _write_entries(registry, [])
        alive, stale = _stale_cleanup.count_stale_entries(str(registry.parent.parent))
        assert (alive, stale) == (0, 0)


class TestWarnIfTooManyStale:
    """``warn_if_too_many_stale`` only warns above the threshold."""

    def test_no_warning_below_threshold(self, registry, caplog):
        _write_entries(registry, [{"pid": 2**31 - 2}] * 5)
        with patch.object(_stale_cleanup, "_pid_alive", return_value=False):
            with caplog.at_level(logging.WARNING, logger=_stale_cleanup.__name__):
                stale = _stale_cleanup.warn_if_too_many_stale(threshold=10, registry_dir=str(registry.parent.parent))
        assert stale == 5
        assert caplog.messages == []

    def test_warning_above_threshold(self, registry, caplog):
        _write_entries(registry, [{"pid": 2**31 - 2 - i} for i in range(15)])
        with patch.object(_stale_cleanup, "_pid_alive", return_value=False):
            with caplog.at_level(logging.WARNING, logger=_stale_cleanup.__name__):
                stale = _stale_cleanup.warn_if_too_many_stale(threshold=10, registry_dir=str(registry.parent.parent))
        assert stale == 15
        assert any("stale Maya instance" in m for m in caplog.messages)

    def test_never_raises(self, tmp_path, caplog):
        # Force count_stale_entries to raise; helper must swallow it.
        with patch.object(_stale_cleanup, "count_stale_entries", side_effect=RuntimeError("boom")):
            assert _stale_cleanup.warn_if_too_many_stale(registry_dir=str(tmp_path)) == 0

    def test_real_pid_check_with_self(self, registry):
        """Smoke test: own PID counts as alive, large PID as stale."""
        _write_entries(registry, [{"pid": os.getpid()}, {"pid": 2**31 - 2}])
        alive, stale = _stale_cleanup.count_stale_entries(str(registry.parent.parent))
        assert alive == 1
        assert stale == 1
