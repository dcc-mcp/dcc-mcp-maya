"""Tests for ``dcc_mcp_maya._pyexec.auto_correct`` (issue #125).

Validates that ``DCC_MCP_PYTHON_EXECUTABLE`` is auto-corrected when the user
sets it to a DCC GUI binary instead of the headless Python sibling.

See: https://github.com/loonghao/dcc-mcp-maya/issues/125
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import sys
from unittest.mock import patch

# Import local modules
from dcc_mcp_maya import _pyexec


class TestAutoCorrect:
    """Tests for the ``auto_correct`` helper."""

    def test_returns_none_when_unset(self):
        """No env var → no work to do, returns None."""
        env = os.environ.copy()
        env.pop(_pyexec.ENV_VAR, None)
        with patch.dict(os.environ, env, clear=True):
            assert _pyexec.auto_correct() is None
            assert _pyexec.ENV_VAR not in os.environ

    def test_returns_none_when_blank(self):
        """Blank env var is treated as unset."""
        with patch.dict(os.environ, {_pyexec.ENV_VAR: "   "}, clear=False):
            assert _pyexec.auto_correct() is None

    def test_python_interpreter_unchanged(self):
        """A real Python interpreter must be left untouched."""
        with patch.dict(os.environ, {_pyexec.ENV_VAR: sys.executable}, clear=False):
            assert _pyexec.auto_correct() == sys.executable
            assert os.environ[_pyexec.ENV_VAR] == sys.executable

    def test_corrects_when_helper_returns_sibling(self):
        """When the core helper finds a sibling, env var is rewritten and returned."""
        original = "C:/Program Files/Autodesk/Maya2025/bin/maya.exe"
        sibling = "C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe"

        def fake_correct(p):
            return sibling if p == original else p

        def fake_is_gui(p):
            return p == original

        with patch.object(_pyexec, "is_gui_executable", fake_is_gui), patch.object(
            _pyexec, "correct_python_executable", fake_correct
        ):
            with patch.dict(os.environ, {_pyexec.ENV_VAR: original}, clear=False):
                assert _pyexec.auto_correct() == sibling
                assert os.environ[_pyexec.ENV_VAR] == sibling

    def test_idempotent(self):
        """A second call after correction is a no-op."""
        sibling = "C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe"

        def fake_correct(p):
            return p  # already a python interpreter

        def fake_is_gui(p):
            return False

        with patch.object(_pyexec, "is_gui_executable", fake_is_gui), patch.object(
            _pyexec, "correct_python_executable", fake_correct
        ):
            with patch.dict(os.environ, {_pyexec.ENV_VAR: sibling}, clear=False):
                first = _pyexec.auto_correct()
                second = _pyexec.auto_correct()
                assert first == second == sibling
                assert os.environ[_pyexec.ENV_VAR] == sibling

    def test_warns_when_gui_with_no_sibling(self, caplog):
        """If the helper returns the value unchanged but flags it as a GUI binary,
        a warning is emitted so the user understands the upcoming subprocess
        failure."""
        gui = "C:/some/orphan/maya.exe"

        def fake_correct(p):
            return p

        def fake_is_gui(p):
            return True

        with patch.object(_pyexec, "is_gui_executable", fake_is_gui), patch.object(
            _pyexec, "correct_python_executable", fake_correct
        ):
            with patch.dict(os.environ, {_pyexec.ENV_VAR: gui}, clear=False):
                with caplog.at_level(logging.WARNING, logger=_pyexec.__name__):
                    assert _pyexec.auto_correct() == gui
                # Match either a true correction warning or the no-sibling warning.
                assert any("GUI executable" in m or "headless" in m for m in caplog.messages)

    def test_non_gui_path_preserved_verbatim(self):
        """Arbitrary user-supplied paths must not be normalised or rewritten."""
        original = "/custom/mayapy"  # forward slashes, no GUI binary

        def fake_correct(p):
            return "\\custom\\mayapy"  # core normalises slashes — must be ignored

        def fake_is_gui(p):
            return False

        with patch.object(_pyexec, "is_gui_executable", fake_is_gui), patch.object(
            _pyexec, "correct_python_executable", fake_correct
        ):
            with patch.dict(os.environ, {_pyexec.ENV_VAR: original}, clear=False):
                assert _pyexec.auto_correct() == original
                assert os.environ[_pyexec.ENV_VAR] == original

    def test_real_helpers_importable(self):
        """Smoke test against the actual core helpers."""
        assert callable(_pyexec.is_gui_executable)
        assert callable(_pyexec.correct_python_executable)
        # A python interpreter must round-trip unchanged (allow Path return).
        assert os.fspath(_pyexec.correct_python_executable(sys.executable)) == sys.executable

    def test_custom_env_var_name(self):
        """The helper accepts a custom env-var name for forward compatibility."""
        custom_name = "TEST_PYEXEC_AUTOCORRECT"
        env = os.environ.copy()
        env.pop(custom_name, None)
        with patch.dict(os.environ, env, clear=True):
            assert _pyexec.auto_correct(custom_name) is None
