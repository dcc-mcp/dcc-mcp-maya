"""Unit tests for fail-closed Maya mutation receipts."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from conftest import wire_named_undo_queue

from dcc_mcp_maya._mutation import MayaUndoChunk


def test_undo_chunk_refuses_mutation_when_maya_undo_is_disabled():
    cmds = MagicMock()
    wire_named_undo_queue(cmds, undo_enabled=False)
    transaction = MayaUndoChunk(cmds, "verified_mutation")

    with pytest.raises(RuntimeError, match="undo must be enabled"):
        transaction.begin()

    # ``call.kwargs`` was added after Python 3.7. Maya 2022's unittest.mock
    # otherwise treats that attribute access as another truthy mock call.
    assert not any(call[1].get("openChunk") for call in cmds.undoInfo.call_args_list)

    receipt = transaction.rollback(lambda: True)

    # No chunk was ever opened, so no undo item is owned. A truthy caller
    # verifier must not be reported as a verified rollback (issue #607).
    assert receipt == {
        "rollback_attempted": False,
        "rollback_verified": False,
        "rollback_skipped_reason": "undo_item_not_owned",
    }
    cmds.undo.assert_not_called()


def test_undo_chunk_surfaces_incomplete_rollback_without_exception_text():
    cmds = MagicMock()
    wire_named_undo_queue(cmds)
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
    # Each invocation owns a unique chunk name, so a foreign chunk that happens
    # to reuse the human-readable name cannot be mistaken for ours (issue #607).
    open_calls = [call for call in cmds.undoInfo.call_args_list if call[1].get("openChunk")]
    assert len(open_calls) == 1
    assert open_calls[0][1]["chunkName"].startswith("verified_mutation__")
    cmds.undoInfo.assert_any_call(closeChunk=True)
