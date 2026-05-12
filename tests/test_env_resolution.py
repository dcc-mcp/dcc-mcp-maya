"""Tests for ``dcc_mcp_maya._env`` env-var resolution helpers (issue #127)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya import _env


class TestResolveMetricsEnabled:
    def test_explicit_true(self):
        with patch.dict(os.environ, {_env.ENV_METRICS: "0"}):
            assert _env.resolve_metrics_enabled(True) is True

    def test_explicit_false(self):
        with patch.dict(os.environ, {_env.ENV_METRICS: "1"}):
            assert _env.resolve_metrics_enabled(False) is False

    def test_env_one(self):
        with patch.dict(os.environ, {_env.ENV_METRICS: "1"}):
            assert _env.resolve_metrics_enabled(None) is True

    def test_env_zero_or_unset(self):
        env = os.environ.copy()
        env.pop(_env.ENV_METRICS, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_metrics_enabled(None) is False
        with patch.dict(os.environ, {_env.ENV_METRICS: "0"}):
            assert _env.resolve_metrics_enabled(None) is False


class TestResolveJobStorage:
    def test_explicit_path_wins(self, tmp_path):
        path = str(tmp_path / "jobs.db")
        assert _env.resolve_job_storage(path) == path

    def test_explicit_empty_disables_persistence(self):
        assert _env.resolve_job_storage("") == ""

    def test_env_var_used(self, tmp_path):
        path = str(tmp_path / "from-env.db")
        with patch.dict(os.environ, {_env.ENV_JOB_STORAGE: path}):
            assert _env.resolve_job_storage(None) == path

    def test_default_under_data_dir(self):
        env = os.environ.copy()
        env.pop(_env.ENV_JOB_STORAGE, None)
        with patch.dict(os.environ, env, clear=True):
            result = _env.resolve_job_storage(None)
        # Either we got a real default path, or the data-dir helper failed
        # gracefully (returned None) — both are acceptable.
        assert result is None or result.endswith(_env.DEFAULT_JOB_DB_FILENAME)


class TestResolveJobRecovery:
    @pytest.mark.parametrize("explicit", ["drop", "DROP", " drop "])
    def test_explicit_drop_normalised(self, explicit):
        assert _env.resolve_job_recovery(explicit) == "drop"

    @pytest.mark.parametrize("explicit", ["requeue", "REQUEUE", " requeue "])
    def test_explicit_requeue_normalised(self, explicit):
        assert _env.resolve_job_recovery(explicit) == "requeue"

    def test_unknown_collapses_to_drop(self):
        assert _env.resolve_job_recovery("garbage") == "drop"

    def test_env_used_when_none(self):
        with patch.dict(os.environ, {_env.ENV_JOB_RECOVERY: "requeue"}):
            assert _env.resolve_job_recovery(None) == "requeue"

    def test_default_when_unset(self):
        env = os.environ.copy()
        env.pop(_env.ENV_JOB_RECOVERY, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_job_recovery(None) == "drop"


class TestResolveWindowTitle:
    def test_explicit_wins(self):
        with patch.dict(os.environ, {_env.ENV_WINDOW_TITLE: "Other"}):
            assert _env.resolve_window_title("Custom") == "Custom"

    def test_env_used_when_none(self):
        with patch.dict(os.environ, {_env.ENV_WINDOW_TITLE: "  My Maya  "}):
            assert _env.resolve_window_title(None) == "My Maya"

    def test_blank_treated_as_none(self):
        env = os.environ.copy()
        env.pop(_env.ENV_WINDOW_TITLE, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_window_title(None) is None
