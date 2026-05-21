"""Unit tests for :mod:`dcc_mcp_maya.context_snapshot` (issues #163, #165).

These tests exercise the Maya context snapshot provider without a live
Maya: a fake ``cmds`` is injected via the ``cmds_provider`` parameter so
we can assert every branch of the collector — including the headless /
unavailable fallback — deterministically.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dcc_mcp_maya import _recovery_dialog
from dcc_mcp_maya.context_snapshot import (
    MayaContextSnapshotProvider,
    collect_gateway_metadata,
    make_snapshot_provider,
)

# ---------------------------------------------------------------------------
# Fake ``cmds`` factory
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_recovery_dialog_state():
    _recovery_dialog.reset_for_tests()
    yield
    _recovery_dialog.reset_for_tests()


def _fake_cmds(**overrides):
    """Return a MagicMock that behaves like ``maya.cmds`` for our probes."""
    cmds = MagicMock(name="cmds")
    cmds.file.return_value = overrides.get("scene", "/projects/shot.ma")
    cmds.ls.return_value = overrides.get("selection", ["pCube1"])
    cmds.currentTime.return_value = overrides.get("frame", 1001)
    cmds.playbackOptions.side_effect = lambda **kw: (
        overrides.get("start", 1001.0) if kw.get("min") else overrides.get("end", 1100.0)
    )
    cmds.upAxis.return_value = overrides.get("up_axis", "y")
    cmds.currentUnit.return_value = overrides.get("units", "cm")
    cmds.about.return_value = overrides.get("version", "2025")

    # The cmds.file call is invoked twice — once with ``sceneName=True`` and
    # once with ``modified=True``.  A side_effect routes correctly.
    def _file(*args, **kwargs):
        if kwargs.get("sceneName"):
            return overrides.get("scene", "/projects/shot.ma")
        if kwargs.get("modified"):
            return overrides.get("modified", False)
        return None

    cmds.file.side_effect = _file
    return cmds


# ---------------------------------------------------------------------------
# Basic collection
# ---------------------------------------------------------------------------


def test_provider_collects_full_snapshot_when_maya_available():
    provider = MayaContextSnapshotProvider(cmds_provider=lambda: _fake_cmds())
    snap = provider()

    assert snap["dcc"] == "maya"
    assert snap["available"] is True
    assert snap["scene"] == "/projects/shot.ma"
    assert snap["scene_modified"] is False
    assert snap["selection"] == ["pCube1"]
    assert snap["frame"] == 1001
    assert snap["frame_range"] == [1001, 1100]
    assert snap["up_axis"] == "y"
    assert snap["units"] == "cm"
    assert snap["version"] == "2025"
    assert snap["display_name"] == "Maya 2025 — shot.ma"
    assert snap["pid"] > 0


def test_provider_returns_stub_when_cmds_unavailable():
    provider = MayaContextSnapshotProvider(cmds_provider=lambda: None)
    snap = provider()
    assert snap == {"dcc": "maya", "pid": pytest.approx(snap["pid"]), "available": False}


def test_provider_survives_cmds_factory_exception():
    def boom():
        raise RuntimeError("maya not initialised")

    provider = MayaContextSnapshotProvider(cmds_provider=boom)
    snap = provider()
    assert snap["available"] is False
    assert snap["dcc"] == "maya"


def test_provider_survives_cmds_method_exception():
    """Individual cmds.* failures must not break the whole snapshot."""
    cmds = MagicMock()
    # ``file`` raises — scene + modified become None.
    cmds.file.side_effect = RuntimeError("no scene")
    cmds.ls.return_value = []
    cmds.currentTime.return_value = 0
    cmds.playbackOptions.return_value = 0
    cmds.upAxis.return_value = "y"
    cmds.currentUnit.return_value = "cm"
    cmds.about.return_value = "2025"

    provider = MayaContextSnapshotProvider(cmds_provider=lambda: cmds)
    snap = provider()

    assert snap["available"] is True
    assert "scene" not in snap
    assert "scene_modified" not in snap
    assert snap["selection"] == []
    assert snap["version"] == "2025"
    # Display name falls back to version-only form.
    assert snap["display_name"] == "Maya 2025"


def test_provider_returns_fresh_dict_each_call():
    provider = MayaContextSnapshotProvider(cmds_provider=lambda: _fake_cmds(selection=["a"]))
    snap1 = provider()
    snap2 = provider()
    assert snap1 is not snap2
    # Mutating one must not affect the other.
    snap1["selection"].append("extra")
    assert snap2["selection"] == ["a"]


def test_provider_includes_recovery_dialog_status_when_present():
    widget = type(
        "Widget",
        (),
        {
            "windowTitle": lambda self: "Maya has stopped working",
            "isVisible": lambda self: True,
        },
    )()
    _recovery_dialog.scan_recovery_dialog(qt_widgets=[widget], auto_dismiss=False)

    provider = MayaContextSnapshotProvider(cmds_provider=lambda: _fake_cmds())
    snap = provider()

    assert snap["maya_recovered"] is True
    assert snap["maya_status"] == "recovery_dialog_detected"
    assert snap["maya_recovery_dialog"]["title"] == "Maya has stopped working"


# ---------------------------------------------------------------------------
# collect_gateway_metadata
# ---------------------------------------------------------------------------


def test_collect_gateway_metadata_single_document():
    provider = MayaContextSnapshotProvider(cmds_provider=lambda: _fake_cmds(scene="/p/a.ma"))
    meta = collect_gateway_metadata(provider)
    assert meta["scene"] == "/p/a.ma"
    assert meta["version"] == "2025"
    assert meta["documents"] == ["/p/a.ma"]
    assert meta["display_name"] == "Maya 2025 — a.ma"


def test_collect_gateway_metadata_no_scene_produces_empty_documents():
    def no_scene_cmds():
        cmds = _fake_cmds()
        cmds.file.side_effect = None
        cmds.file.return_value = ""  # empty scene path
        return cmds

    provider = MayaContextSnapshotProvider(cmds_provider=no_scene_cmds)
    meta = collect_gateway_metadata(provider)
    assert meta["scene"] is None
    assert meta["documents"] == []
    assert meta["version"] == "2025"


def test_collect_gateway_metadata_headless_returns_all_none_or_empty():
    provider = MayaContextSnapshotProvider(cmds_provider=lambda: None)
    meta = collect_gateway_metadata(provider)
    assert meta == {
        "scene": None,
        "version": None,
        "documents": [],
        "display_name": None,
    }


def test_collect_gateway_metadata_defaults_to_builtin_provider():
    # Without injection it must still succeed (headless fallback).
    meta = collect_gateway_metadata()
    assert set(meta) == {"scene", "version", "documents", "display_name"}


# ---------------------------------------------------------------------------
# make_snapshot_provider
# ---------------------------------------------------------------------------


def test_make_snapshot_provider_returns_callable_provider():
    provider = make_snapshot_provider(cmds_provider=lambda: _fake_cmds())
    assert callable(provider)
    assert provider()["available"] is True
