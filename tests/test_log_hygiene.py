"""Tests for Maya log hygiene helpers."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from dcc_mcp_maya._log_hygiene import prune_maya_logs


def test_prune_maya_logs_calls_core_pruner_when_available():
    core = MagicMock()
    core.prune_old_logs.return_value = {"removed": 2}

    with patch.dict(sys.modules, {"dcc_mcp_core": core}):
        result = prune_maya_logs(retention_days=7, max_total_size_mb=50)

    assert result == {"removed": 2}
    core.prune_old_logs.assert_called_once_with(retention_days=7, max_total_size_mb=50)


def test_prune_maya_logs_noops_when_core_symbol_missing():
    core = MagicMock()
    del core.prune_old_logs

    with patch.dict(sys.modules, {"dcc_mcp_core": core}):
        assert prune_maya_logs() is None


def test_prune_maya_logs_swallows_core_failures():
    core = MagicMock()
    core.prune_old_logs.side_effect = RuntimeError("disk busy")

    with patch.dict(sys.modules, {"dcc_mcp_core": core}):
        assert prune_maya_logs() is None
