"""Unit tests for scripting-skill enhancements shipped for issues #151 & #153.

The tests run without a live Maya session — ``maya.api.OpenMaya`` is mocked
when needed so the safe-fallback path in
:class:`dcc_mcp_maya._maya_output.MayaOutputCapture` is exercised.  E2E
coverage that requires ``mayapy`` lives in ``tests/e2e/test_scripting_e2e.py``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest
import yaml

from tests.conftest import load_skill_script

# ---------------------------------------------------------------------------
# MayaOutputCapture — safe no-op when Maya is unavailable
# ---------------------------------------------------------------------------


class TestMayaOutputCaptureFallback:
    """Without ``maya.api.OpenMaya`` importable, the helper must degrade cleanly."""

    def test_no_maya_returns_empty_buffers(self):
        from dcc_mcp_maya._maya_output import MayaOutputCapture

        # Both module candidates unavailable — ensure the context manager
        # still enters and exits without raising.
        with patch.dict(
            sys.modules, {"maya.api": None, "maya.api.OpenMaya": None, "maya": None, "maya.OpenMaya": None}
        ):
            with MayaOutputCapture() as cap:
                pass
        assert cap.stdout == ""
        assert cap.stderr == ""

    def test_callback_registration_failure_is_swallowed(self):
        """If MCommandMessage.addCommandOutputCallback raises, we continue."""
        from dcc_mcp_maya._maya_output import MayaOutputCapture

        fake_module = MagicMock()
        fake_module.MCommandMessage.addCommandOutputCallback.side_effect = RuntimeError("callback not available")

        with patch("dcc_mcp_maya._maya_output._load_openmaya", return_value=fake_module):
            with MayaOutputCapture() as cap:
                pass

        assert cap.stdout == ""
        assert cap.stderr == ""

    def test_info_routed_to_stdout_error_to_stderr(self):
        """Verify the callback classifies MCommandMessage output types correctly."""
        from dcc_mcp_maya._maya_output import (
            _MSG_TYPE_ERROR,
            _MSG_TYPE_INFO,
            _MSG_TYPE_RESULT,
            _MSG_TYPE_WARNING,
            MayaOutputCapture,
        )

        captured_callback: dict = {}

        fake_module = MagicMock()

        def _fake_add(cb):
            captured_callback["cb"] = cb
            return "fake-callback-id"

        fake_module.MCommandMessage.addCommandOutputCallback.side_effect = _fake_add

        with patch("dcc_mcp_maya._maya_output._load_openmaya", return_value=fake_module):
            with MayaOutputCapture() as cap:
                cb = captured_callback["cb"]
                cb("hello-info", _MSG_TYPE_INFO)
                cb("a-result", _MSG_TYPE_RESULT)
                cb("a-warning", _MSG_TYPE_WARNING)
                cb("an-error", _MSG_TYPE_ERROR)

        assert "hello-info" in cap.stdout
        assert "a-result" in cap.stdout
        assert "a-warning" in cap.stderr
        assert "an-error" in cap.stderr
        # Callback must be removed on __exit__.
        fake_module.MMessage.removeCallback.assert_called_once_with("fake-callback-id")


# ---------------------------------------------------------------------------
# execute_python — deferred path cooperatively honours cancellation
# ---------------------------------------------------------------------------


class TestExecutePythonDeferCancellation:
    """``defer=True`` wires the core cancellation token into poll + tracer."""

    def test_poll_callback_raises_on_job_cancel(self):
        """When the per-job cancel flag is set, the poll callback re-raises."""
        mod = load_skill_script("maya-scripting", "execute_python")

        # Import local modules
        from dcc_mcp_core.cancellation import CancelledError

        from dcc_mcp_maya.dispatcher.job import _current_job, _JobEntry

        job = _JobEntry(
            request_id="rid-cancel-test",
            affinity="main",
            task=lambda: None,
        )
        token = _current_job.set(job)
        try:
            # Build the poll callback directly without running the script:
            # mod._run_deferred would immediately execute the code in the
            # no-maya fallback path, masking the cancellation semantics we
            # want to exercise.
            deferred = mod._run_deferred(
                code="# intentionally empty — no-op snippet",
                capture_output=False,
                timeout_secs=60.0,
            )
            # Simulate the client cancelling the request.
            job.cancel()
            with pytest.raises(CancelledError):
                deferred.check_is_finished()
        finally:
            _current_job.reset(token)

    def test_defer_without_maya_runs_inline(self):
        """In plain pytest, ``_run_deferred`` falls back to inline execution."""
        mod = load_skill_script("maya-scripting", "execute_python")

        deferred = mod._run_deferred(
            code="result = 2 + 3",
            capture_output=False,
            timeout_secs=10.0,
        )
        # Inline fallback populates the result *before* the DeferredToolResult
        # is constructed, so the poll callback returns a completed envelope.
        envelope = deferred.check_is_finished()
        assert envelope is not None
        assert envelope.get("success") is True


# ---------------------------------------------------------------------------
# tools.yaml contract
# ---------------------------------------------------------------------------


class TestToolsYamlContract:
    """Schema-level guarantees for the ``execute_python`` tool declaration."""

    def _load_tools(self) -> dict:
        path = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting" / "tools.yaml"
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def test_execute_python_exposes_defer_in_schema(self):
        """`defer` must be declared as a boolean input so clients can opt in."""
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        props = tool.get("inputSchema", {}).get("properties", {})
        assert "defer" in props, (
            "execute_python must advertise the 'defer' parameter so MCP clients "
            "can opt into the non-blocking execution path (issue #153)."
        )
        assert props["defer"].get("type") == "boolean"

    def test_execute_python_description_mentions_defer(self):
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        desc = tool["description"]
        assert "defer" in desc.lower()

    def test_execute_python_description_mentions_maya_stderr_capture(self):
        """Description should advertise the MCommandMessage capture (issue #151)."""
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        desc = tool["description"].lower()
        # Accept either `cmds.warning` or `script editor` wording — both describe
        # the native-channel capture we added.
        assert "cmds.warning" in desc or "script editor" in desc

    def test_execute_python_still_declares_main_affinity(self):
        """Even though `defer=True` is async, the tool still touches Maya."""
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        assert tool["affinity"] == "main"


# ---------------------------------------------------------------------------
# execute_python inline — stdout capture merges Python + Maya channels
# ---------------------------------------------------------------------------


class TestInlineCaptureMerging:
    """``_run_inline`` concatenates Python and Maya capture buffers."""

    def test_print_goes_to_stdout(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        # Ensure MayaOutputCapture no-ops (no Maya available).
        envelope = mod._run_inline("print('hello-stdout')", capture_output=True)
        assert envelope["success"] is True
        ctx = envelope.get("context", {})
        # stdout key must be populated; MayaOutputCapture is a no-op here.
        assert "hello-stdout" in ctx.get("stdout", "")

    def test_merge_capture_helper(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        # Both empty → empty
        assert mod._merge_capture("", "") == ""
        # Only one side populated
        assert mod._merge_capture("a\n", "") == "a\n"
        assert mod._merge_capture("", "b") == "b"
        # Both populated, primary already ends with newline
        assert mod._merge_capture("a\n", "b") == "a\nb"
        # Both populated, primary missing newline
        assert mod._merge_capture("a", "b") == "a\nb"
