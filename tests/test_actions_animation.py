"""Tests for Maya animation actions (maya.cmds is mocked)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


@pytest.fixture()
def mock_maya():
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.setKeyframe.return_value = 3
    cmds_mock.keyframe.return_value = [1.0, 10.0, 20.0]
    cmds_mock.currentTime.return_value = 1.0

    with patch.dict(
        sys.modules,
        {
            "maya": MagicMock(cmds=cmds_mock, utils=MagicMock()),
            "maya.cmds": cmds_mock,
            "maya.utils": MagicMock(),
        },
    ):
        yield cmds_mock


def _reload():
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]


def _no_maya():
    return patch.dict(sys.modules, {"maya": None, "maya.cmds": None})


# ---------------------------------------------------------------------------
# set_keyframe
# ---------------------------------------------------------------------------

class TestSetKeyframe:
    def test_set_keyframe_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import set_keyframe

        result = set_keyframe("pSphere1")
        assert result["success"] is True
        assert result["context"]["keyframe_count"] == 3

    def test_set_keyframe_with_time_and_attrs(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import set_keyframe

        result = set_keyframe("pSphere1", attributes=["tx", "ty"], time=10.0)
        assert result["success"] is True
        mock_maya.setKeyframe.assert_called()

    def test_set_keyframe_with_value(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import set_keyframe

        result = set_keyframe("pSphere1", attributes=["tx"], time=5.0, value=10.0)
        assert result["success"] is True
        mock_maya.setAttr.assert_called_with("pSphere1.tx", 10.0)

    def test_set_keyframe_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.animation import set_keyframe

        result = set_keyframe("ghost")
        assert result["success"] is False

    def test_set_keyframe_exception(self, mock_maya):
        _reload()
        mock_maya.setKeyframe.side_effect = RuntimeError("locked")
        from dcc_mcp_maya.actions.animation import set_keyframe

        result = set_keyframe("pSphere1")
        assert result["success"] is False

    def test_set_keyframe_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.animation import set_keyframe

            result = set_keyframe("pSphere1")
        assert result["success"] is False
        assert "Maya not available" in result["message"]


# ---------------------------------------------------------------------------
# get_keyframes
# ---------------------------------------------------------------------------

class TestGetKeyframes:
    def test_get_keyframes_all(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import get_keyframes

        result = get_keyframes("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 3
        assert result["context"]["keyframes"] == [1.0, 10.0, 20.0]

    def test_get_keyframes_with_attribute(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import get_keyframes

        result = get_keyframes("pSphere1", attribute="tx")
        assert result["success"] is True
        assert result["context"]["attribute"] == "tx"

    def test_get_keyframes_none_result(self, mock_maya):
        _reload()
        mock_maya.keyframe.return_value = None
        from dcc_mcp_maya.actions.animation import get_keyframes

        result = get_keyframes("pSphere1")
        assert result["success"] is True
        assert result["context"]["keyframes"] == []

    def test_get_keyframes_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.animation import get_keyframes

        result = get_keyframes("ghost")
        assert result["success"] is False

    def test_get_keyframes_exception(self, mock_maya):
        _reload()
        mock_maya.keyframe.side_effect = RuntimeError("keyframe error")
        from dcc_mcp_maya.actions.animation import get_keyframes

        result = get_keyframes("pSphere1")
        assert result["success"] is False

    def test_get_keyframes_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.animation import get_keyframes

            result = get_keyframes("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# set_timeline
# ---------------------------------------------------------------------------

class TestSetTimeline:
    def test_set_timeline_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import set_timeline

        result = set_timeline()
        assert result["success"] is True
        assert result["context"]["start_frame"] == 1.0
        assert result["context"]["end_frame"] == 120.0

    def test_set_timeline_custom(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import set_timeline

        result = set_timeline(start_frame=0.0, end_frame=240.0, min_frame=-10.0, max_frame=250.0)
        assert result["success"] is True
        mock_maya.playbackOptions.assert_called_with(
            minTime=0.0, maxTime=240.0,
            animationStartTime=-10.0, animationEndTime=250.0,
        )

    def test_set_timeline_defaults_min_max(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import set_timeline

        result = set_timeline(start_frame=5.0, end_frame=100.0)
        assert result["context"]["min_frame"] == 5.0
        assert result["context"]["max_frame"] == 100.0

    def test_set_timeline_exception(self, mock_maya):
        _reload()
        mock_maya.playbackOptions.side_effect = RuntimeError("timeline error")
        from dcc_mcp_maya.actions.animation import set_timeline

        result = set_timeline()
        assert result["success"] is False

    def test_set_timeline_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.animation import set_timeline

            result = set_timeline()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# get/set current time
# ---------------------------------------------------------------------------

class TestCurrentTime:
    def test_get_current_time(self, mock_maya):
        _reload()
        mock_maya.currentTime.return_value = 42.0
        from dcc_mcp_maya.actions.animation import get_current_time

        result = get_current_time()
        assert result["success"] is True
        assert result["context"]["current_time"] == 42.0

    def test_get_current_time_exception(self, mock_maya):
        _reload()
        mock_maya.currentTime.side_effect = RuntimeError("time error")
        from dcc_mcp_maya.actions.animation import get_current_time

        result = get_current_time()
        assert result["success"] is False

    def test_get_current_time_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.animation import get_current_time

            result = get_current_time()
        assert result["success"] is False

    def test_set_current_time(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import set_current_time

        result = set_current_time(10.0)
        assert result["success"] is True
        assert result["context"]["current_time"] == 10.0
        mock_maya.currentTime.assert_called_with(10.0, update=True)

    def test_set_current_time_exception(self, mock_maya):
        _reload()
        mock_maya.currentTime.side_effect = RuntimeError("seek error")
        from dcc_mcp_maya.actions.animation import set_current_time

        result = set_current_time(10.0)
        assert result["success"] is False

    def test_set_current_time_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.animation import set_current_time

            result = set_current_time(10.0)
        assert result["success"] is False
