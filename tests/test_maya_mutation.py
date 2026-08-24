"""Unit tests for fail-closed Maya mutation receipts."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dcc_mcp_maya._mutation import MayaUndoChunk


def test_undo_chunk_refuses_mutation_when_maya_undo_is_disabled():
    cmds = MagicMock()
    cmds.undoInfo.return_value = False
    transaction = MayaUndoChunk(cmds, "verified_mutation")

    with pytest.raises(RuntimeError, match="undo must be enabled"):
        transaction.begin()

    assert not any(call.kwargs.get("openChunk") for call in cmds.undoInfo.call_args_list)

    receipt = transaction.rollback(lambda: True)

    assert receipt == {
        "rollback_attempted": False,
        "rollback_verified": True,
    }
    cmds.undo.assert_not_called()


def test_undo_chunk_surfaces_incomplete_rollback_without_exception_text():
    cmds = MagicMock()
    cmds.undoInfo.return_value = True
    cmds.undo.side_effect = RuntimeError("local scene detail must not leak")
    transaction = MayaUndoChunk(cmds, "verified_mutation")
    transaction.begin()

    receipt = transaction.rollback(lambda: True)

    assert receipt == {
        "rollback_attempted": True,
        "rollback_verified": False,
        "rollback_error_type": "RuntimeError",
    }
    assert "local scene detail" not in str(receipt)
    cmds.undoInfo.assert_any_call(openChunk=True, chunkName="verified_mutation")
    cmds.undoInfo.assert_any_call(closeChunk=True)
