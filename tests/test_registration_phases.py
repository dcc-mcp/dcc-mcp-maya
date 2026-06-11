"""Tests for Maya builtin registration phases."""

from __future__ import annotations

import builtins
import importlib.util
import sys
from unittest.mock import MagicMock

import pytest

from dcc_mcp_maya import _registration


class _RecordingPhase(_registration.RegistrationPhase):
    def __init__(self, name: str, calls: list, fail: bool = False) -> None:
        self.name = name
        self._calls = calls
        self._fail = fail

    def run(self, context: _registration.RegistrationContext) -> None:
        self._calls.append((self.name, context.server))
        if self._fail:
            raise RuntimeError("boom")


def test_default_registration_phases_are_ordered() -> None:
    names = [phase.name for phase in _registration.default_registration_phases()]
    assert names == [
        "core_builtin_actions",
        "metadata_driven_tools",
        "strict_skill_scan",
        "capability_manifest",
        "project_tools",
        "resources",
    ]


def test_run_registration_phases_records_success_and_failure() -> None:
    calls = []
    server = MagicMock()
    context = _registration.RegistrationContext(server=server)

    report = _registration.run_registration_phases(
        [
            _RecordingPhase("one", calls),
            _RecordingPhase("two", calls, fail=True),
            _RecordingPhase("three", calls),
        ],
        context,
    )

    assert [outcome.name for outcome in report.outcomes] == ["one", "two", "three"]
    assert [outcome.success for outcome in report.outcomes] == [True, False, True]
    assert report.success is False
    assert report.outcomes[1].error == "boom"
    assert [call[0] for call in calls] == ["one", "two", "three"]


def test_strict_scan_value_error_remains_fatal() -> None:
    server = MagicMock()
    server._run_strict_skill_scan_if_enabled.side_effect = ValueError("bad skill")
    context = _registration.RegistrationContext(server=server, strict_scan=True)

    with pytest.raises(ValueError):
        _registration.run_registration_phases([_registration.StrictSkillScanPhase()], context)


def test_phase_methods_delegate_to_server() -> None:
    server = MagicMock()
    context = _registration.RegistrationContext(
        server=server,
        extra_skill_paths=["extras"],
        include_bundled=False,
        strict_scan=True,
    )

    for phase in _registration.default_registration_phases():
        phase.run(context)

    server._register_core_builtin_actions.assert_called_once_with(context)
    server._register_metadata_driven_tools.assert_called_once_with(context)
    server._run_strict_skill_scan_if_enabled.assert_called_once_with(True, ["extras"], False)
    server._register_capability_manifest_tool.assert_called_once_with()
    server._attach_project_tools.assert_called_once_with()
    server._attach_resources.assert_called_once_with()


def test_registration_module_falls_back_when_core_helper_is_missing(monkeypatch) -> None:
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "dcc_mcp_core._registration":
            raise ModuleNotFoundError("No module named 'dcc_mcp_core._registration'", name=name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module_path = _registration.__file__
    spec = importlib.util.spec_from_file_location("_maya_registration_fallback_test", module_path)
    fallback = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = fallback
    spec.loader.exec_module(fallback)

    calls = []
    server = MagicMock()
    context = fallback.RegistrationContext(server=server)
    report = fallback.run_registration_phases(
        [
            _RecordingPhase("one", calls),
            _RecordingPhase("two", calls, fail=True),
            _RecordingPhase("three", calls),
        ],
        context,
    )

    assert [outcome.name for outcome in report.outcomes] == ["one", "two", "three"]
    assert [outcome.success for outcome in report.outcomes] == [True, False, True]
    assert report.success is False
    assert report.outcomes[1].error == "boom"
