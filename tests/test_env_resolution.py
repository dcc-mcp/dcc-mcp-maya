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


class TestResolveMinimalFlag:
    def test_explicit_true_wins(self):
        with patch.dict(os.environ, {_env.ENV_MINIMAL: "0"}):
            assert _env.resolve_minimal_flag(True) is True

    def test_explicit_false_wins(self):
        with patch.dict(os.environ, {_env.ENV_MINIMAL: "1"}):
            assert _env.resolve_minimal_flag(False) is False

    def test_env_zero_disables(self):
        env = os.environ.copy()
        env[_env.ENV_MINIMAL] = "0"
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_minimal_flag(None) is False

    def test_env_one_enables(self):
        with patch.dict(os.environ, {_env.ENV_MINIMAL: "1"}):
            assert _env.resolve_minimal_flag(None) is True

    def test_default_when_unset(self):
        env = os.environ.copy()
        env.pop(_env.ENV_MINIMAL, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_minimal_flag(None) is True


class TestResolveDefaultTools:
    def test_unset_returns_none(self):
        env = os.environ.copy()
        env.pop(_env.ENV_DEFAULT_TOOLS, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_default_tools() is None

    def test_blank_returns_none(self):
        with patch.dict(os.environ, {_env.ENV_DEFAULT_TOOLS: ""}):
            assert _env.resolve_default_tools() is None

    def test_single_skill(self):
        with patch.dict(os.environ, {_env.ENV_DEFAULT_TOOLS: "maya-scene"}):
            assert _env.resolve_default_tools() == {"maya-scene": []}

    def test_csv_skills_with_whitespace(self):
        with patch.dict(os.environ, {_env.ENV_DEFAULT_TOOLS: "  maya-scene , maya-mesh-ops "}):
            result = _env.resolve_default_tools()
            assert result is not None
            assert set(result.keys()) == {"maya-scene", "maya-mesh-ops"}

    def test_skips_empty_tokens(self):
        with patch.dict(os.environ, {_env.ENV_DEFAULT_TOOLS: ",a,,b,"}):
            result = _env.resolve_default_tools()
            assert result is not None
            assert set(result.keys()) == {"a", "b"}


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


# ─────────────────────────────────────────────────────────────────────────────
# Gateway tool-exposure mode (core 0.14.22 / dcc-mcp-core#652)
# ─────────────────────────────────────────────────────────────────────────────


class TestResolveToolExposure:
    """Cover the full priority table for ``resolve_tool_exposure``.

    The resolver is the only place where a typo in
    ``DCC_MCP_MAYA_TOOL_EXPOSURE`` can be contained; every downstream
    caller trusts its output implicitly, so we exercise every branch.
    """

    def test_unset_returns_none(self):
        env = os.environ.copy()
        env.pop(_env.ENV_TOOL_EXPOSURE, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_tool_exposure(None) is None

    def test_explicit_argument_overrides_env(self):
        with patch.dict(os.environ, {_env.ENV_TOOL_EXPOSURE: "full"}):
            assert _env.resolve_tool_exposure("slim") == "slim"

    def test_env_var_used_when_argument_missing(self):
        with patch.dict(os.environ, {_env.ENV_TOOL_EXPOSURE: "rest"}):
            assert _env.resolve_tool_exposure(None) == "rest"

    @pytest.mark.parametrize("mode", list(_env.VALID_TOOL_EXPOSURE_MODES))
    def test_every_valid_mode_round_trips(self, mode):
        with patch.dict(os.environ, {_env.ENV_TOOL_EXPOSURE: mode}):
            assert _env.resolve_tool_exposure(None) == mode

    def test_uppercase_and_whitespace_normalised(self):
        # Operators on Windows occasionally set env vars mixed-case; we
        # accept that as long as the normalised lowercase value maps to
        # a known mode.
        with patch.dict(os.environ, {_env.ENV_TOOL_EXPOSURE: "  SLIM  "}):
            assert _env.resolve_tool_exposure(None) == "slim"

    def test_invalid_value_falls_back_to_none_and_logs(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="dcc_mcp_maya._env"):
            with patch.dict(os.environ, {_env.ENV_TOOL_EXPOSURE: "bogus"}):
                assert _env.resolve_tool_exposure(None) is None
        assert any("bogus" in rec.getMessage() for rec in caplog.records)

    def test_empty_string_is_treated_as_unset(self):
        with patch.dict(os.environ, {_env.ENV_TOOL_EXPOSURE: ""}):
            assert _env.resolve_tool_exposure(None) is None


class TestResolveCursorSafeToolNames:
    """``DCC_MCP_MAYA_CURSOR_SAFE_TOOL_NAMES`` is a tri-state resolver:

    * ``True`` / ``False`` when the caller intentionally opts in or out.
    * ``None`` when unset, so callers leave the inner-config default
      alone instead of flipping it to an arbitrary value.
    """

    def test_unset_returns_none(self):
        env = os.environ.copy()
        env.pop(_env.ENV_CURSOR_SAFE_TOOL_NAMES, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_cursor_safe_tool_names(None) is None

    def test_explicit_argument_true(self):
        # Explicit argument wins even when env says otherwise.
        with patch.dict(os.environ, {_env.ENV_CURSOR_SAFE_TOOL_NAMES: "0"}):
            assert _env.resolve_cursor_safe_tool_names(True) is True

    def test_explicit_argument_false(self):
        with patch.dict(os.environ, {_env.ENV_CURSOR_SAFE_TOOL_NAMES: "1"}):
            assert _env.resolve_cursor_safe_tool_names(False) is False

    @pytest.mark.parametrize("raw", ["0", "false", "FALSE", "no", "off"])
    def test_env_disables_when_falsy(self, raw):
        with patch.dict(os.environ, {_env.ENV_CURSOR_SAFE_TOOL_NAMES: raw}):
            assert _env.resolve_cursor_safe_tool_names(None) is False

    @pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on"])
    def test_env_enables_when_truthy(self, raw):
        with patch.dict(os.environ, {_env.ENV_CURSOR_SAFE_TOOL_NAMES: raw}):
            assert _env.resolve_cursor_safe_tool_names(None) is True

    def test_invalid_value_returns_none(self):
        # We intentionally preserve the inner default rather than
        # collapsing to ``False`` — flipping a boolean silently on typos
        # would be a footgun for operators.
        with patch.dict(os.environ, {_env.ENV_CURSOR_SAFE_TOOL_NAMES: "maybe"}):
            assert _env.resolve_cursor_safe_tool_names(None) is None
