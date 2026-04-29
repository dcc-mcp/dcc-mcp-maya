"""Tests for ``dcc_mcp_maya._version_probe`` (issue #127)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import local modules
from dcc_mcp_maya import _version_probe


class TestMayaAvailable:
    def test_returns_true_when_maya_cmds_importable(self):
        fake_cmds = MagicMock()
        with patch.dict(sys.modules, {"maya": MagicMock(), "maya.cmds": fake_cmds}):
            assert _version_probe.maya_available() is True

    def test_returns_false_when_maya_missing(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            assert _version_probe.maya_available() is False


class TestGetMayaVersionString:
    def test_returns_unknown_when_unavailable(self):
        with patch.object(_version_probe, "maya_available", return_value=False):
            assert _version_probe.get_maya_version_string() == _version_probe.UNKNOWN_VERSION

    def _install_fake_maya(self, about_returns=None, about_raises=None):
        """Install a fresh ``maya``/``maya.cmds`` pair so the lazy import sees us."""
        fake_cmds = MagicMock(name="maya.cmds")
        if about_raises is not None:
            fake_cmds.about.side_effect = about_raises
        else:
            fake_cmds.about.return_value = about_returns
        fake_maya = MagicMock(name="maya")
        fake_maya.cmds = fake_cmds
        return {"maya": fake_maya, "maya.cmds": fake_cmds}, fake_cmds

    def test_returns_about_value_when_available(self):
        modules, fake_cmds = self._install_fake_maya(about_returns="2025")
        with patch.object(_version_probe, "maya_available", return_value=True):
            with patch.dict(sys.modules, modules):
                assert _version_probe.get_maya_version_string() == "2025"
                fake_cmds.about.assert_called_once_with(version=True)

    def test_returns_unknown_on_exception(self):
        modules, _ = self._install_fake_maya(about_raises=RuntimeError("kaboom"))
        with patch.object(_version_probe, "maya_available", return_value=True):
            with patch.dict(sys.modules, modules):
                assert _version_probe.get_maya_version_string() == _version_probe.UNKNOWN_VERSION

    def test_coerces_non_string_to_str(self):
        modules, _ = self._install_fake_maya(about_returns=2025)
        with patch.object(_version_probe, "maya_available", return_value=True):
            with patch.dict(sys.modules, modules):
                assert _version_probe.get_maya_version_string() == "2025"
