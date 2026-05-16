"""Unit tests for ``dcc_mcp_maya._maya_commandport_hygiene`` (issue #148).

Mocks ``maya.cmds`` / ``maya.mel`` because these are not importable
in the standard CI matrix (no Maya install). The corresponding
real-Maya behaviour is exercised separately by the mayapy E2E test
in ``tests/e2e/test_maya_commandport_hygiene_e2e.py``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya import _maya_commandport_hygiene as _commandport

# ────────────────────────────────────────────────────────────────────────
# _is_disabled_by_env
# ────────────────────────────────────────────────────────────────────────


class TestIsDisabledByEnv:
    @pytest.mark.parametrize("value", ["0", " 0", "0 "])
    def test_disabled_when_env_is_zero(self, monkeypatch, value):
        monkeypatch.setenv(_commandport.ENV_DISABLE_WARNING, value)
        assert _commandport._is_disabled_by_env() is True

    @pytest.mark.parametrize("value", ["", "1", "true", "yes", "no", "00"])
    def test_not_disabled_for_other_values(self, monkeypatch, value):
        monkeypatch.setenv(_commandport.ENV_DISABLE_WARNING, value)
        assert _commandport._is_disabled_by_env() is False

    def test_default_is_not_disabled(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        assert _commandport._is_disabled_by_env() is False


# ────────────────────────────────────────────────────────────────────────
# _list_open_ports
# ────────────────────────────────────────────────────────────────────────


def _patch_mel(eval_return):
    fake_mel = MagicMock()
    fake_mel.eval = MagicMock(return_value=eval_return)
    fake_maya = MagicMock()
    fake_maya.mel = fake_mel
    return patch.dict(sys.modules, {"maya": fake_maya, "maya.mel": fake_mel})


class TestListOpenPorts:
    def test_returns_empty_when_maya_not_installed(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.mel", None)
        # ``import maya.mel`` with sentinel None raises ImportError on Python 3.
        assert _commandport._list_open_ports() == []

    def test_returns_empty_when_mel_returns_none(self):
        with _patch_mel(None):
            assert _commandport._list_open_ports() == []

    def test_normalises_single_string(self):
        with _patch_mel("mayaCommand"):
            assert _commandport._list_open_ports() == ["mayaCommand"]

    def test_returns_empty_when_mel_returns_empty_string(self):
        with _patch_mel(""):
            assert _commandport._list_open_ports() == []

    def test_normalises_list_and_strips_falsy(self):
        with _patch_mel(["a", "", None, "b"]):
            assert _commandport._list_open_ports() == ["a", "b"]

    def test_swallows_mel_eval_exception(self):
        fake_mel = MagicMock()
        fake_mel.eval = MagicMock(side_effect=RuntimeError("mel boom"))
        fake_maya = MagicMock()
        fake_maya.mel = fake_mel
        with patch.dict(sys.modules, {"maya": fake_maya, "maya.mel": fake_mel}):
            assert _commandport._list_open_ports() == []

    def test_returns_empty_when_iter_fails(self):
        # Non-string non-iterable should fall through TypeError handler.
        with _patch_mel(42):
            assert _commandport._list_open_ports() == []


# ────────────────────────────────────────────────────────────────────────
# close_default_commandport
# ────────────────────────────────────────────────────────────────────────


class TestCloseDefaultCommandPort:
    def test_zero_when_env_disabled(self, monkeypatch):
        monkeypatch.setenv(_commandport.ENV_CLOSE_DEFAULT, "0")
        fake_cmds = MagicMock()
        fake_maya = MagicMock()
        fake_maya.cmds = fake_cmds
        with patch.dict(sys.modules, {"maya": fake_maya, "maya.cmds": fake_cmds}):
            assert _commandport.close_default_commandport() == 0
        fake_cmds.commandPort.assert_not_called()

    def test_closes_open_default_aliases(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_CLOSE_DEFAULT, raising=False)
        fake_cmds = MagicMock()
        fake_cmds.commandPort.side_effect = [True, None, True, None]
        fake_maya = MagicMock()
        fake_maya.cmds = fake_cmds

        with patch.dict(sys.modules, {"maya": fake_maya, "maya.cmds": fake_cmds}):
            assert _commandport.close_default_commandport() == 2

        kwargs_seq = [c[1] for c in fake_cmds.commandPort.call_args_list]
        assert kwargs_seq[0] == {"query": True, "sourceType": "mel"}
        assert fake_cmds.commandPort.call_args_list[0][0] == (":50007",)
        assert kwargs_seq[1] == {"name": ":50007", "close": True}
        assert kwargs_seq[2] == {"query": True, "sourceType": "mel"}
        assert fake_cmds.commandPort.call_args_list[2][0] == ("commandportDefault",)
        assert kwargs_seq[3] == {"name": "commandportDefault", "close": True}

    def test_ignores_closed_default_port(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_CLOSE_DEFAULT, raising=False)
        fake_cmds = MagicMock()
        fake_cmds.commandPort.return_value = False
        fake_maya = MagicMock()
        fake_maya.cmds = fake_cmds

        with patch.dict(sys.modules, {"maya": fake_maya, "maya.cmds": fake_cmds}):
            assert _commandport.close_default_commandport() == 0


# ────────────────────────────────────────────────────────────────────────
# suppress_security_warnings
# ────────────────────────────────────────────────────────────────────────


class TestSuppressSecurityWarnings:
    def test_zero_when_env_disabled(self, monkeypatch):
        monkeypatch.setenv(_commandport.ENV_DISABLE_WARNING, "0")
        with patch.object(_commandport, "_list_open_ports") as ports:
            assert _commandport.suppress_security_warnings() == 0
            ports.assert_not_called()

    def test_zero_when_no_open_ports(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        with patch.object(_commandport, "_list_open_ports", return_value=[]):
            assert _commandport.suppress_security_warnings() == 0

    def test_calls_close_then_reopen_per_port(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        fake_cmds = MagicMock()
        fake_cmds.commandPort.side_effect = [
            "mel",
            None,
            None,
            "python",
            None,
            None,
        ]
        fake_maya = MagicMock()
        fake_maya.cmds = fake_cmds
        with patch.object(_commandport, "_list_open_ports", return_value=["p1", "p2"]):
            with patch.dict(sys.modules, {"maya": fake_maya, "maya.cmds": fake_cmds}):
                assert _commandport.suppress_security_warnings() == 2
        # Each port: query sourceType, close, reopen preserving sourceType.
        assert fake_cmds.commandPort.call_count == 6
        kwargs_seq = [c[1] for c in fake_cmds.commandPort.call_args_list]
        assert kwargs_seq[0] == {"name": "p1", "query": True, "sourceType": True}
        assert kwargs_seq[1] == {"name": "p1", "close": True}
        assert kwargs_seq[2] == {"name": "p1", "securityWarning": False, "sourceType": "mel"}
        assert kwargs_seq[3] == {"name": "p2", "query": True, "sourceType": True}
        assert kwargs_seq[4] == {"name": "p2", "close": True}
        assert kwargs_seq[5] == {"name": "p2", "securityWarning": False, "sourceType": "python"}

    def test_configure_commandport_hygiene_runs_close_then_suppress(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        monkeypatch.delenv(_commandport.ENV_CLOSE_DEFAULT, raising=False)
        with patch.object(_commandport, "close_default_commandport", return_value=1) as close_fn:
            with patch.object(_commandport, "suppress_security_warnings", return_value=2) as suppress_fn:
                _commandport.configure_commandport_hygiene()
        close_fn.assert_called_once_with()
        suppress_fn.assert_called_once_with()

    def test_partial_failure_counts_only_successes(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        fake_cmds = MagicMock()

        # Make port "bad" raise; "ok" succeeds (close + reopen).
        def cmd(**kw):
            if kw.get("name") == "bad" and kw.get("close"):
                raise RuntimeError("close failed")

        fake_cmds.commandPort = MagicMock(side_effect=cmd)
        fake_maya = MagicMock()
        fake_maya.cmds = fake_cmds
        with patch.object(_commandport, "_list_open_ports", return_value=["bad", "ok"]):
            with patch.dict(sys.modules, {"maya": fake_maya, "maya.cmds": fake_cmds}):
                assert _commandport.suppress_security_warnings() == 1

    def test_zero_when_cmds_unimportable(self, monkeypatch):
        monkeypatch.delenv(_commandport.ENV_DISABLE_WARNING, raising=False)
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        with patch.object(_commandport, "_list_open_ports", return_value=["only"]):
            assert _commandport.suppress_security_warnings() == 0
