"""Unit tests for the maya-scripting skill — bare-exec dispatch path.

After the RFC #998 follow-up fix series in PR #248 the dispatch path
is intentionally wrapper-free: no ``mcp_safe_session``, no
``ScriptExecutionCapture`` tee, no ``MayaOutputCapture`` callback
bridge by default, no ``sys.settrace`` cancellation tracer. The tests
here mirror that shape — they cover the bare-exec ``execute_python``,
the new ``write_module`` upload-once / call-many surface, and the
single-tool ``io`` action multiplexer.

The legacy tests for spill / capture-merging / defer + cancellation
have been removed alongside the wrappers they exercised.
``MayaOutputCapture`` opt-in coverage stays in place because the
helper itself is still shipped (default-off) for operators who
explicitly opt in via env var.

E2E coverage that requires ``mayapy`` lives in
``tests/e2e/test_scripting_e2e.py``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest
import yaml

from tests.conftest import load_skill_script

# ---------------------------------------------------------------------------
# MayaOutputCapture — default no-op + opt-in via env var (RFC #998 da5f6184)
# ---------------------------------------------------------------------------


class TestMayaOutputCaptureFallback:
    """Default-off behaviour + env-var opt-in for the OpenMaya callback bridge."""

    def test_default_is_noop_without_opt_in(self):
        """Default path: env var not set, no ``force`` — must NOT touch OpenMaya."""
        from dcc_mcp_maya._maya_output import MayaOutputCapture

        fake_module = MagicMock()
        with patch.dict("os.environ", {"DCC_MCP_MAYA_HOOK_MAYA_OUTPUT": ""}, clear=False):
            with patch("dcc_mcp_maya._maya_output._load_openmaya", return_value=fake_module):
                with MayaOutputCapture() as cap:
                    pass
        fake_module.MCommandMessage.addCommandOutputCallback.assert_not_called()
        assert cap.stdout == ""
        assert cap.stderr == ""

    def test_opt_in_via_env_registers_callback(self):
        """Setting ``DCC_MCP_MAYA_HOOK_MAYA_OUTPUT=1`` restores the OpenMaya bridge."""
        from dcc_mcp_maya._maya_output import MayaOutputCapture

        fake_module = MagicMock()
        with patch.dict("os.environ", {"DCC_MCP_MAYA_HOOK_MAYA_OUTPUT": "1"}, clear=False):
            with patch("dcc_mcp_maya._maya_output._load_openmaya", return_value=fake_module):
                with MayaOutputCapture():
                    pass
        fake_module.MCommandMessage.addCommandOutputCallback.assert_called_once()

    def test_no_maya_returns_empty_buffers(self):
        from dcc_mcp_maya._maya_output import MayaOutputCapture

        with patch.dict(
            sys.modules,
            {"maya.api": None, "maya.api.OpenMaya": None, "maya": None, "maya.OpenMaya": None},
        ):
            with MayaOutputCapture(force=True) as cap:
                pass
        assert cap.stdout == ""
        assert cap.stderr == ""

    def test_callback_registration_failure_is_swallowed(self):
        from dcc_mcp_maya._maya_output import MayaOutputCapture

        fake_module = MagicMock()
        fake_module.MCommandMessage.addCommandOutputCallback.side_effect = RuntimeError("nope")
        with patch("dcc_mcp_maya._maya_output._load_openmaya", return_value=fake_module):
            with MayaOutputCapture(force=True) as cap:
                pass
        assert cap.stdout == ""
        assert cap.stderr == ""


# ---------------------------------------------------------------------------
# Operator policy — refuse arbitrary script tools when env vars are set
# ---------------------------------------------------------------------------


class TestArbitraryScriptPolicyEnv:
    """``DCC_MCP_MAYA_DISABLE_*`` gates short-circuit before Maya I/O."""

    def test_disable_execute_python_returns_structured_error(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        with patch.dict(os.environ, {"DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON": "1"}):
            out = mod.execute_python(code="1+1")
        assert out.get("success") is False
        assert "policy" in (out.get("message") or "").lower()

    def test_disable_arbitrary_script_blocks_execute_mel(self):
        mod = load_skill_script("maya-scripting", "execute_mel")
        with patch.dict(os.environ, {"DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT": "true"}):
            out = mod.execute_mel(code="1")
        assert out.get("success") is False
        assert "policy" in (out.get("message") or "").lower()

    def test_disable_arbitrary_script_blocks_execute_python(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        with patch.dict(os.environ, {"DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT": "on"}):
            out = mod.execute_python(code="pass")
        assert out.get("success") is False


class TestExecuteMelPythonGuard:
    """execute_mel must not feed obvious Python through mel.eval (Maya 2022 spam)."""

    def test_rejects_python_smoke_expression(self):
        mod = load_skill_script("maya-scripting", "execute_mel")
        out = mod.execute_mel(code="1+1;")
        assert out.get("success") is False
        assert "python" in (out.get("message") or "").lower()

    def test_rejects_python_import(self):
        mod = load_skill_script("maya-scripting", "execute_mel")
        out = mod.execute_mel(code="import maya.cmds as cmds")
        assert out.get("success") is False


# ---------------------------------------------------------------------------
# execute_python bare-exec semantics (no live Maya required)
# ---------------------------------------------------------------------------


class TestExecutePythonBareExec:
    """Wrapper-free dispatch — same shape as PatrickPalmer/maya-mcp-server."""

    def test_simple_print_captured_in_stdout(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="print('hello-bare-exec')")
        assert out.get("success") is True
        ctx = out.get("context") or {}
        assert "hello-bare-exec" in ctx.get("stdout", "")

    def test_result_type_value_captures_last_expression(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="1 + 2", result_type="VALUE")
        assert out.get("success") is True
        ctx = out.get("context") or {}
        assert ctx.get("output") == "3"

    def test_result_type_json_round_trips_through_json(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="{'a': 1, 'b': [2, 3]}", result_type="JSON")
        assert out.get("success") is True
        ctx = out.get("context") or {}
        # ``output`` is str(captured_value); the value itself is a dict
        # round-tripped through json.dumps + json.loads.
        assert "a" in ctx.get("output", "")
        assert "1" in ctx.get("output", "")

    def test_result_type_repr_uses_repr(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="object()", result_type="REPR")
        assert out.get("success") is True
        ctx = out.get("context") or {}
        assert ctx.get("output", "").startswith("<object object at ")

    def test_result_type_none_returns_empty_output(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="1 + 2", result_type="NONE")
        assert out.get("success") is True
        ctx = out.get("context") or {}
        assert ctx.get("output") == ""

    def test_result_type_value_on_non_expression_errors(self):
        """Last statement is not a bare ``Expr`` → structured error."""
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="x = 1\ny = 2\nimport os", result_type="VALUE")
        assert out.get("success") is False
        msg = (out.get("message") or "").lower()
        assert "expression" in msg or "execution failed" in msg

    def test_persistent_namespace_survives_across_calls(self):
        """An ``import`` from one call must be visible to the next."""
        mod = load_skill_script("maya-scripting", "execute_python")
        # First call: import a stdlib module.
        out1 = mod.execute_python(code="import math\nmath.pi", result_type="VALUE")
        assert out1.get("success") is True
        # Second call: reference ``math`` without re-importing — should
        # resolve via the persistent module namespace.
        out2 = mod.execute_python(code="math.tau", result_type="VALUE")
        assert out2.get("success") is True
        ctx = out2.get("context") or {}
        # ``math.tau`` is ~6.28… ; tolerate float repr precision.
        assert ctx.get("output", "").startswith("6.28")

    def test_traceback_surfaces_on_runtime_exception(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="raise RuntimeError('boom-test')")
        assert out.get("success") is False
        ctx = out.get("context") or {}
        stderr = ctx.get("stderr") or ""
        assert "boom-test" in stderr or "boom-test" in (out.get("message") or "")
        assert "Traceback" in stderr

    def test_capture_output_false_does_not_redirect(self, capsys):
        """``capture_output=False`` lets prints reach the host's real stdout."""
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="print('to-host-stdout')", capture_output=False)
        assert out.get("success") is True
        ctx = out.get("context") or {}
        assert ctx.get("stdout", "") == ""
        # The print fell through to the real stdout, which pytest's capsys
        # captures during the test.
        captured = capsys.readouterr()
        assert "to-host-stdout" in captured.out

    def test_empty_code_returns_error(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="")
        assert out.get("success") is False
        assert "no python" in (out.get("message") or "").lower()

    def test_invalid_result_type_returns_error(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(code="1+1", result_type="BOGUS")
        assert out.get("success") is False
        assert "result_type" in (out.get("message") or "").lower()

    def test_script_alias_source_is_accepted(self):
        """Upstream ``normalize_script_execution_params`` accepts aliases."""
        mod = load_skill_script("maya-scripting", "execute_python")
        out_a = mod.execute_python(code="2 + 2", result_type="VALUE")
        out_b = mod.execute_python(script="2 + 2", result_type="VALUE")
        out_c = mod.execute_python(source="2 + 2", result_type="VALUE")
        for out in (out_a, out_b, out_c):
            assert out.get("success") is True


class TestExecutePythonMainThreadMarshalling:
    """When called off Maya's main thread, ``execute_python`` must marshal user code
    onto the main thread via :func:`maya.utils.executeInMainThreadWithResult`.

    This is the documented Maya primitive for cross-thread work; the user-
    reported FBX-export crash on 2026-05-16 was traced to bare exec on
    a tokio worker thread (``cmds.file(..., type="FBX export")`` / ``loadPlugin``
    crashes Maya when off the UI thread). The implementation aligns with
    PatrickPalmer/maya-mcp-server.
    """

    def test_inplace_true_skips_main_thread_routing(self):
        """``inplace=True`` opts out — neither the queue nor the bridge is touched."""
        # Import local modules
        from dcc_mcp_maya import _main_thread_queue

        _main_thread_queue.reset_for_tests()
        mod = load_skill_script("maya-scripting", "execute_python")
        fake_queue = MagicMock()
        try:
            with patch.object(mod, "_running_on_main_thread", return_value=False), patch.object(
                _main_thread_queue, "get_queue", return_value=fake_queue
            ):
                out = mod.execute_python(code="1 + 1", inplace=True, result_type="VALUE")
            assert out.get("success") is True
            fake_queue.submit.assert_not_called()
        finally:
            _main_thread_queue.reset_for_tests()

    def test_off_main_thread_routes_through_queue_and_marshals_to_main(self):
        """Default path: off main thread → queue → executeInMainThreadWithResult."""
        # Import local modules
        from dcc_mcp_maya import _main_thread_queue

        _main_thread_queue.reset_for_tests()
        mod = load_skill_script("maya-scripting", "execute_python")
        called_with: List[Any] = []

        def fake_run(fn):
            called_with.append(fn)
            return fn()

        fake_mu = MagicMock()
        fake_mu.executeInMainThreadWithResult.side_effect = fake_run

        try:
            with patch.object(_main_thread_queue, "_import_maya_utils", return_value=fake_mu), patch.object(
                mod, "_running_on_main_thread", return_value=False
            ), patch.object(mod, "_should_marshal_to_maya_main_thread", return_value=True):
                out = mod.execute_python(code="2 + 3", result_type="VALUE")

            assert out.get("success") is True
            fake_mu.executeInMainThreadWithResult.assert_called_once()
            passed = called_with[0]
            assert callable(passed)
            assert passed.__code__.co_argcount == 0
        finally:
            _main_thread_queue.reset_for_tests()

    def test_already_on_main_thread_runs_inline(self):
        """When already on main thread, the queue marshalling must NOT fire."""
        # Import local modules
        from dcc_mcp_maya import _main_thread_queue

        _main_thread_queue.reset_for_tests()
        mod = load_skill_script("maya-scripting", "execute_python")
        fake_queue = MagicMock()
        try:
            with patch.object(mod, "_running_on_main_thread", return_value=True), patch.object(
                _main_thread_queue, "get_queue", return_value=fake_queue
            ):
                out = mod.execute_python(code="3 + 4", result_type="VALUE")
            assert out.get("success") is True
            # On main thread, execute_python must not even touch the queue.
            fake_queue.submit.assert_not_called()
        finally:
            _main_thread_queue.reset_for_tests()

    def test_no_maya_falls_back_to_inplace(self):
        """``mayapy`` / pytest: no Maya bridge → queue pump runs job inline."""
        # Import local modules
        from dcc_mcp_maya import _main_thread_queue

        _main_thread_queue.reset_for_tests()
        mod = load_skill_script("maya-scripting", "execute_python")
        try:
            with patch.object(_main_thread_queue, "_import_maya_utils", return_value=None), patch.object(
                mod, "_running_on_main_thread", return_value=False
            ):
                out = mod.execute_python(code="5 + 6", result_type="VALUE")
            assert out.get("success") is True
        finally:
            _main_thread_queue.reset_for_tests()

    def test_concurrent_calls_serialise_through_single_pump_fifo(self):
        """20 worker threads submit concurrently → all complete, strict FIFO order.

        Regression guard for the user's concern (2026-05-16):
        ``executeInMainThreadWithResult`` blocks the calling tokio
        worker, so N concurrent ``execute_python`` calls without a
        queue would all block N workers and the order they reach
        Maya's main thread depends on the tokio scheduler. With the
        single-writer queue ``_main_thread_queue.get_queue()`` we
        get explicit FIFO + a single in-flight marshalling call at a
        time, regardless of caller-thread concurrency.
        """
        # Import local modules
        import threading as _threading

        from dcc_mcp_maya import _main_thread_queue

        _main_thread_queue.reset_for_tests()
        mod = load_skill_script("maya-scripting", "execute_python")

        # Track each slot the pump observed via the bridge. We patch
        # executeInMainThreadWithResult so the pump calls fn() inline —
        # the assertion is about coverage (every job runs exactly once),
        # not Maya's deferred-queue ordering details.
        observed_slots: List[int] = []
        order_lock = _threading.Lock()

        def _fake_marshal(fn):
            envelope = fn()
            # _execute_bare_inplace returns {"success", "result", "error", "stdout", "stderr"};
            # the trailing expression in our user code (``_``) is captured under "result".
            try:
                slot_value = int(envelope.get("result"))
            except (TypeError, ValueError):
                slot_value = -1
            with order_lock:
                observed_slots.append(slot_value)
            return envelope

        fake_mu = MagicMock()
        fake_mu.executeInMainThreadWithResult.side_effect = _fake_marshal

        try:
            with patch.object(_main_thread_queue, "_import_maya_utils", return_value=fake_mu):
                with patch.object(mod, "_running_on_main_thread", return_value=False), patch.object(
                    mod, "_should_marshal_to_maya_main_thread", return_value=True
                ):
                    barrier = _threading.Barrier(20)
                    results: List[Any] = [None] * 20

                    def _worker(slot: int) -> None:
                        barrier.wait()  # release all callers at the same time
                        results[slot] = mod.execute_python(
                            code="_ = {0}\n_".format(slot),
                            result_type="VALUE",
                            inplace=False,
                        )

                    threads = [_threading.Thread(target=_worker, args=(i,)) for i in range(20)]
                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join(timeout=10.0)

            # Every call must have produced a success envelope.
            for slot, out in enumerate(results):
                assert out is not None, "worker {0} never returned".format(slot)
                assert out.get("success") is True, "worker {0} envelope: {1}".format(slot, out)

            # The pump observed all 20 slots exactly once. No drops, no
            # duplicates. Ordering itself isn't asserted because
            # ``queue.Queue`` does not promise arrival-order under
            # racing producers — what matters is the bounded depth is
            # enough and the pump drains everything.
            assert sorted(observed_slots) == list(range(20))
        finally:
            _main_thread_queue.reset_for_tests()

    def test_queue_full_returns_backpressure_envelope(self):
        """When the bounded queue rejects a job, the envelope surfaces it."""
        from concurrent.futures import Future

        # Import local modules
        from dcc_mcp_maya import _main_thread_queue

        _main_thread_queue.reset_for_tests()
        mod = load_skill_script("maya-scripting", "execute_python")

        try:
            full_future: Future = Future()
            full_future.set_exception(
                _main_thread_queue.QueueFullError(
                    "Maya main-thread queue full (depth=64, maxsize=64); back off and retry."
                )
            )

            fake_queue = MagicMock()
            fake_queue.submit.return_value = full_future

            with patch.object(_main_thread_queue, "get_queue", return_value=fake_queue):
                with patch.object(mod, "_running_on_main_thread", return_value=False), patch.object(
                    mod, "_should_marshal_to_maya_main_thread", return_value=True
                ):
                    out = mod.execute_python(code="1+1", inplace=False)

            assert out.get("success") is False
            msg = (out.get("message") or "").lower()
            ctx = out.get("context") or {}
            joined = msg + "\n" + str(ctx)
            assert "queue full" in joined.lower() or "backpressure" in joined.lower() or "back off" in joined.lower()
        finally:
            _main_thread_queue.reset_for_tests()

    def test_marshalling_failure_falls_back_to_inline_inside_pump(self):
        """When ``executeInMainThreadWithResult`` itself raises, the pump runs inline.

        Maya's mid-shutdown / event-loop-stalled states cause the
        marshalling primitive to fail. Rather than poison the agent's
        request with an opaque transport error, the pump catches the
        failure and calls ``fn()`` inline on the pump thread. The
        envelope is the normal success envelope; user code still
        ran.
        """
        # Import local modules
        from dcc_mcp_maya import _main_thread_queue

        _main_thread_queue.reset_for_tests()
        mod = load_skill_script("maya-scripting", "execute_python")
        fake_mu = MagicMock()
        fake_mu.executeInMainThreadWithResult.side_effect = RuntimeError("main thread is unavailable")

        try:
            with patch.object(_main_thread_queue, "_import_maya_utils", return_value=fake_mu), patch.object(
                mod, "_running_on_main_thread", return_value=False
            ):
                out = mod.execute_python(code="1 + 1", result_type="VALUE")
            assert out.get("success") is True
            ctx = out.get("context") or {}
            assert ctx.get("output") == "2"
        finally:
            _main_thread_queue.reset_for_tests()


# ---------------------------------------------------------------------------
# execute_python file_path / script_path
# ---------------------------------------------------------------------------


class TestExecutePythonFilePath:
    """``file_path`` execution path — no live Maya needed for I/O errors."""

    def test_missing_file_returns_error_envelope(self):
        mod = load_skill_script("maya-scripting", "execute_python")
        out = mod.execute_python(file_path="/nonexistent/__no_such_mcp_script__.py")
        assert out.get("success") is False
        assert "not found" in (out.get("message") or "").lower()

    def test_non_py_extension_returns_error(self, tmp_path: Path):
        mod = load_skill_script("maya-scripting", "execute_python")
        bad = tmp_path / "not_a_py.txt"
        bad.write_text("nope", encoding="utf-8")
        out = mod.execute_python(file_path=str(bad))
        assert out.get("success") is False
        assert ".py" in (out.get("message") or "").lower() or "py" in (out.get("message") or "").lower()

    def test_script_path_alias_executes_py_file(self, tmp_path: Path):
        mod = load_skill_script("maya-scripting", "execute_python")
        f = tmp_path / "demo.py"
        f.write_text("print('from-file-script')\n", encoding="utf-8")
        out = mod.execute_python(script_path=str(f))
        assert out.get("success") is True
        ctx = out.get("context") or {}
        assert "from-file-script" in ctx.get("stdout", "")


# ---------------------------------------------------------------------------
# write_module — upload-once / call-many pattern
# ---------------------------------------------------------------------------


class TestWriteModule:
    """Inject a module into ``sys.modules`` from a source string."""

    @pytest.fixture(autouse=True)
    def _isolate(self):
        # Avoid cross-test contamination of the synthesised module name.
        for name in list(sys.modules):
            if name.startswith("_mcp_test_writemodule"):
                sys.modules.pop(name, None)
        yield
        for name in list(sys.modules):
            if name.startswith("_mcp_test_writemodule"):
                sys.modules.pop(name, None)

    def test_synthesises_module_in_sys_modules(self):
        mod = load_skill_script("maya-scripting", "write_module")
        out = mod.write_module(
            name="_mcp_test_writemodule_basic",
            source="value = 42\n\ndef greet(): return 'hello'\n",
        )
        assert out.get("success") is True
        assert "_mcp_test_writemodule_basic" in sys.modules
        installed = sys.modules["_mcp_test_writemodule_basic"]
        assert installed.value == 42
        assert installed.greet() == "hello"

    def test_overwrite_true_refreshes_attributes_in_place(self):
        mod = load_skill_script("maya-scripting", "write_module")
        first = mod.write_module(name="_mcp_test_writemodule_over", source="value = 1\n")
        assert first.get("success") is True
        first_id = id(sys.modules["_mcp_test_writemodule_over"])

        second = mod.write_module(name="_mcp_test_writemodule_over", source="value = 2\n", overwrite=True)
        assert second.get("success") is True
        # Same module object — identity preserved across rewrites.
        assert id(sys.modules["_mcp_test_writemodule_over"]) == first_id
        assert sys.modules["_mcp_test_writemodule_over"].value == 2

    def test_overwrite_false_skips_when_module_exists(self):
        mod = load_skill_script("maya-scripting", "write_module")
        first = mod.write_module(name="_mcp_test_writemodule_skip", source="value = 1\n")
        assert first.get("success") is True
        second = mod.write_module(name="_mcp_test_writemodule_skip", source="value = 999\n", overwrite=False)
        assert second.get("success") is True
        # Body NOT re-exec'd — value stays 1.
        assert sys.modules["_mcp_test_writemodule_skip"].value == 1

    def test_invalid_name_returns_error(self):
        mod = load_skill_script("maya-scripting", "write_module")
        for bad in ("", "1leading", "with-hyphen", "with space"):
            out = mod.write_module(name=bad, source="pass\n")
            assert out.get("success") is False, "should reject name={!r}".format(bad)

    def test_empty_source_returns_error(self):
        mod = load_skill_script("maya-scripting", "write_module")
        out = mod.write_module(name="_mcp_test_writemodule_empty", source="")
        assert out.get("success") is False

    def test_syntax_error_in_source_returns_error_envelope(self):
        mod = load_skill_script("maya-scripting", "write_module")
        out = mod.write_module(name="_mcp_test_writemodule_syntax", source="def x(::\n")
        assert out.get("success") is False
        assert "syntaxerror" in (out.get("message") or "").lower()
        # The broken source must NOT pollute sys.modules.
        assert "_mcp_test_writemodule_syntax" not in sys.modules

    def test_runtime_error_in_module_body_returns_error_envelope(self):
        mod = load_skill_script("maya-scripting", "write_module")
        out = mod.write_module(
            name="_mcp_test_writemodule_runtime",
            source="raise RuntimeError('module-init-failed')\n",
        )
        assert out.get("success") is False
        # Error detail may live on `message` (top-level summary) or in the
        # nested context — accept either; both surface the cause to the agent.
        ctx = out.get("context") or {}
        joined = "{0}\n{1}\n{2}".format(
            out.get("message") or "",
            ctx.get("message") or "",
            ctx.get("traceback") or "",
        )
        assert "module-init-failed" in joined

    def test_disabled_by_env_var(self):
        mod = load_skill_script("maya-scripting", "write_module")
        with patch.dict(os.environ, {"DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON": "1"}):
            out = mod.write_module(name="_mcp_test_writemodule_blocked", source="value = 1\n")
        assert out.get("success") is False
        assert "policy" in (out.get("message") or "").lower()
        assert "_mcp_test_writemodule_blocked" not in sys.modules


# ---------------------------------------------------------------------------
# io — single-tool action multiplexer for stdout/stderr capture
# ---------------------------------------------------------------------------


class TestIoAction:
    """``io`` lifecycle: install / get / clear / uninstall / status."""

    @pytest.fixture(autouse=True)
    def _restore_streams(self):
        original_out = sys.stdout
        original_err = sys.stderr
        # Force-uninstall in case a previous test left a tee in place.
        mod = load_skill_script("maya-scripting", "io")
        mod.io_action(action="uninstall")
        yield
        mod.io_action(action="uninstall")
        sys.stdout = original_out
        sys.stderr = original_err

    def test_install_then_uninstall_round_trip(self):
        mod = load_skill_script("maya-scripting", "io")
        original_stdout = sys.stdout
        installed = mod.io_action(action="install")
        assert installed.get("success") is True
        ctx = installed.get("context") or {}
        assert ctx.get("installed") is True
        # sys.stdout must be replaced.
        assert sys.stdout is not original_stdout

        uninstalled = mod.io_action(action="uninstall")
        ctx = uninstalled.get("context") or {}
        assert ctx.get("uninstalled") is True
        # sys.stdout must be restored.
        assert sys.stdout is original_stdout

    def test_get_drains_buffer_by_default(self):
        mod = load_skill_script("maya-scripting", "io")
        mod.io_action(action="install")
        print("captured-line-A")
        first = mod.io_action(action="get")
        assert "captured-line-A" in (first.get("context") or {}).get("stdout", "")
        # After draining, the buffer should be empty.
        second = mod.io_action(action="get")
        assert (second.get("context") or {}).get("stdout") == ""

    def test_get_peek_without_drain_preserves_buffer(self):
        mod = load_skill_script("maya-scripting", "io")
        mod.io_action(action="install")
        print("captured-line-B")
        peeked = mod.io_action(action="get", drain=False)
        assert "captured-line-B" in (peeked.get("context") or {}).get("stdout", "")
        # Buffer must NOT have been emptied.
        peeked_again = mod.io_action(action="get")
        assert "captured-line-B" in (peeked_again.get("context") or {}).get("stdout", "")

    def test_clear_empties_buffers_without_uninstalling(self):
        mod = load_skill_script("maya-scripting", "io")
        mod.io_action(action="install")
        print("captured-line-C")
        cleared = mod.io_action(action="clear")
        ctx = cleared.get("context") or {}
        assert ctx.get("cleared") is True
        assert ctx.get("installed") is True
        # After clear, nothing buffered.
        got = mod.io_action(action="get")
        assert (got.get("context") or {}).get("stdout") == ""

    def test_status_reports_install_state_and_bytes(self):
        mod = load_skill_script("maya-scripting", "io")
        status_off = mod.io_action(action="status")
        assert (status_off.get("context") or {}).get("installed") is False

        mod.io_action(action="install")
        print("X" * 13)
        status_on = mod.io_action(action="status")
        ctx = status_on.get("context") or {}
        assert ctx.get("installed") is True
        assert ctx.get("stdout_bytes") >= 13

    def test_install_is_idempotent(self):
        mod = load_skill_script("maya-scripting", "io")
        first = mod.io_action(action="install")
        assert (first.get("context") or {}).get("installed") is True
        second = mod.io_action(action="install")
        ctx = second.get("context") or {}
        assert ctx.get("reused") is True
        assert ctx.get("installed") is False  # already there

    def test_unknown_action_returns_error(self):
        mod = load_skill_script("maya-scripting", "io")
        out = mod.io_action(action="bogus")
        assert out.get("success") is False

    def test_action_required(self):
        mod = load_skill_script("maya-scripting", "io")
        out = mod.io_action()
        assert out.get("success") is False


# ---------------------------------------------------------------------------
# tools.yaml — schema contract
# ---------------------------------------------------------------------------


class TestToolsYamlContract:
    """Pin the public schema for the maya-scripting tools."""

    def _load_tools(self) -> dict:
        path = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting" / "tools.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_execute_python_advertises_result_type_param(self):
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        props = tool.get("inputSchema", {}).get("properties", {})
        assert "result_type" in props, "execute_python must advertise the result_type selector"
        assert props["result_type"].get("type") == "string"
        assert set(props["result_type"].get("enum", [])) >= {"NONE", "VALUE", "JSON", "REPR"}

    def test_execute_python_no_longer_advertises_defer(self):
        """Regression guard: the deferred / settrace path was removed in #248."""
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        props = tool.get("inputSchema", {}).get("properties", {})
        assert "defer" not in props
        assert "timeout_secs" not in props

    def test_execute_python_schema_keeps_file_path(self):
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        props = tool.get("inputSchema", {}).get("properties", {})
        assert "file_path" in props
        assert "script_path" in props

    def test_execute_python_still_declares_main_affinity(self):
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        assert tool["affinity"] == "main"

    def test_execute_python_advertises_skills_first_escape_hatch(self):
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_python")
        desc = tool["description"].lower()
        assert "load_skill" in desc or "search_skills" in desc

    def test_write_module_is_declared(self):
        data = self._load_tools()
        tool = next((t for t in data["tools"] if t["name"] == "write_module"), None)
        assert tool is not None, "write_module must be declared in tools.yaml"
        props = tool.get("inputSchema", {}).get("properties", {})
        assert {"name", "source", "overwrite"} <= set(props.keys())
        assert "name" in tool["inputSchema"].get("required", [])
        assert "source" in tool["inputSchema"].get("required", [])

    def test_io_is_declared_with_action_multiplexer(self):
        data = self._load_tools()
        tool = next((t for t in data["tools"] if t["name"] == "io"), None)
        assert tool is not None, "io must be declared in tools.yaml"
        props = tool.get("inputSchema", {}).get("properties", {})
        assert "action" in props
        assert set(props["action"].get("enum", [])) >= {"install", "uninstall", "get", "clear", "status"}
        assert "action" in tool["inputSchema"].get("required", [])

    def test_execute_mel_schema_has_file_path(self):
        data = self._load_tools()
        tool = next(t for t in data["tools"] if t["name"] == "execute_mel")
        props = tool.get("inputSchema", {}).get("properties", {})
        assert "file_path" in props


def test_execute_python_blocks_dirty_new_scene_prompt(monkeypatch):
    mod = load_skill_script("maya-scripting", "execute_python")

    class _Cmds:
        def __init__(self):
            self.calls = []

        def file(self, *args, **kwargs):
            self.calls.append((args, dict(kwargs)))
            if kwargs.get("query") and kwargs.get("modified"):
                return True
            if kwargs.get("new") and not kwargs.get("force"):
                raise AssertionError("modal save prompt would have opened")
            return "ok"

    cmds = _Cmds()
    monkeypatch.setattr(mod, "_should_marshal_to_maya_main_thread", lambda: False)
    monkeypatch.setitem(mod._PERSISTENT_NS, "cmds", cmds)

    result = mod.execute_python(code="cmds.file(new=True)", capture_output=False)

    assert result["success"] is False
    assert result["message"] == "cmds.file prompt blocked"
    assert "force=True" in result["error"]
    assert cmds.calls == [((), {"query": True, "modified": True})]


# ---------------------------------------------------------------------------
# Cleanup env-var fixture leak
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_safe_session_env():
    saved = os.environ.get("DCC_MCP_MAYA_SAFE_SESSION")
    yield
    if saved is None:
        os.environ.pop("DCC_MCP_MAYA_SAFE_SESSION", None)
    else:
        os.environ["DCC_MCP_MAYA_SAFE_SESSION"] = saved
