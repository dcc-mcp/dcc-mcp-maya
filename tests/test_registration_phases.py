"""Tests for Maya builtin registration phases.

Maya re-uses the shared core phase pipeline, so these tests cover the
Maya-facing surface only: that ``default_registration_phases()`` returns
the standard core order, and that the re-exported executor honours the
order / non-fatal-failure contract. Host-hook delegation and fatal-abort
behaviour are covered in dcc-mcp-core's ``test_registration_pipeline``.
"""

from __future__ import annotations

from dcc_mcp_maya import _registration


class _RecordingPhase(_registration.RegistrationPhase):
    def __init__(self, name: str, calls: list, fail: bool = False) -> None:
        self.name = name
        self._calls = calls
        self._fail = fail

    def run(self, context: _registration.RegistrationContext) -> None:
        self._calls.append(self.name)
        if self._fail:
            raise RuntimeError("boom")


def test_default_registration_phases_are_ordered() -> None:
    names = [phase.name for phase in _registration.default_registration_phases()]
    assert names == [
        "core_builtin_actions",
        "strict_skill_scan",
        "metadata_driven_tools",
        "introspect_tools",
        "feedback_tool",
        "qt_ui_inspector",
        "capability_manifest",
        "project_tools",
        "resources",
        "skill_catalog_ready",
    ]


def test_run_registration_phases_records_success_and_failure() -> None:
    calls: list = []
    context = _registration.RegistrationContext(server=object())

    report = _registration.run_registration_phases(
        [
            _RecordingPhase("one", calls),
            _RecordingPhase("two", calls, fail=True),
            _RecordingPhase("three", calls),
        ],
        context,
    )

    # A non-fatal failure must not stop later phases.
    assert calls == ["one", "two", "three"]
    assert [outcome.name for outcome in report.outcomes] == ["one", "two", "three"]
    assert [outcome.success for outcome in report.outcomes] == [True, False, True]
    assert report.success is False
    assert report.outcomes[1].error == "boom"
