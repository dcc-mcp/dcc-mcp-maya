"""Tests for Maya builtin registration phases."""

from __future__ import annotations

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
        "recipes_tools",
        "skill_reference_docs",
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
    server._register_recipes_tools.assert_called_once_with(context)
    server._register_skill_reference_docs_tools.assert_called_once_with(context)
    server._run_strict_skill_scan_if_enabled.assert_called_once_with(True, ["extras"], False)
    server._register_capability_manifest_tool.assert_called_once_with()
    server._attach_project_tools.assert_called_once_with()
    server._attach_resources.assert_called_once_with()
