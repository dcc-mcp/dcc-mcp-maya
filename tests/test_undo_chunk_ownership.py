"""Regression tests for issue #607 — verified Maya undo ownership.

An *open* undo chunk is not proof that Maya recorded a transaction. When the
first write fails before any undoable scene mutation, closing the empty chunk
and calling ``cmds.undo()`` pops the preceding, unrelated user transaction.
The rollback receipt then lies: its verifier only checks the tool's own target
curves, so it reports ``rollback_verified=true`` even though user work was
destroyed.

These tests use a synthetic, in-memory model of Maya's named-chunk undo queue
(no Maya host is started). They reproduce the reporter's scenario at the shared
``MayaUndoChunk`` helper level, which is where every affected skill call sites
its rollback. See GHSA/dcc-mcp-maya#607.
"""

from __future__ import annotations

import pytest

from dcc_mcp_maya._mutation import MayaUndoChunk


class FakeUndoQueue:
    """Minimal model of Maya's named-chunk undo queue (no host, no real cmds).

    Models the documented behaviour that an empty chunk (no undoable writes) is
    discarded on ``closeChunk`` while a chunk that recorded writes becomes one
    undo item named by its ``chunkName``. ``undo()`` pops that top item and runs
    its inverse. Every operation is pure in-memory state — no files, no Maya,
    no external calls.
    """

    def __init__(self):
        self.undo_enabled = True
        self._items = []  # list of (chunk_name, [(plug, old_value), ...])
        self._open_stack = []  # stack of dict(name, writes)
        self.scene = {}  # plug -> value
        self.undo_calls = 0
        self.close_calls = 0
        self.foreign_after_next_close = None
        self.raise_on_undo_name_query = False

    # -- maya.cmds-like surface ------------------------------------------------
    def undoInfo(self, **kwargs):
        query = kwargs.get("query")
        if query and kwargs.get("state"):
            return self.undo_enabled
        if query and kwargs.get("undoName"):
            if self.raise_on_undo_name_query:
                raise RuntimeError("host cannot report undo names")
            return self._items[-1][0] if self._items else None
        if kwargs.get("openChunk"):
            self._open_stack.append({"name": kwargs.get("chunkName"), "writes": []})
            return None
        if kwargs.get("closeChunk"):
            self.close_calls += 1
            if self._open_stack:
                chunk = self._open_stack.pop()
                if chunk["writes"]:
                    # Maya merges a nested chunk into its still-open parent, so
                    # the resulting undo item is named by the outer chunk.
                    owner = self._open_stack[-1]["name"] if self._open_stack else chunk["name"]
                    self._items.append((owner, list(chunk["writes"])))
            if self.foreign_after_next_close is not None:
                self._items.append((self.foreign_after_next_close, []))
                self.foreign_after_next_close = None
            return None
        return None

    def undo(self):
        self.undo_calls += 1
        if not self._items:
            return  # real Maya: undo() on an empty queue is a no-op
        _name, writes = self._items.pop()
        for plug, old in reversed(writes):
            if old is None:
                self.scene.pop(plug, None)
            else:
                self.scene[plug] = old

    # -- helpers to drive the fake scene --------------------------------------
    def succeed_write(self, plug, value):
        """Simulate an undoable command that really mutated the scene."""
        old = self.scene.get(plug)
        self.scene[plug] = value
        if self._open_stack:
            self._open_stack[-1]["writes"].append((plug, old))

    def prior_user_work(self, name="Previous_User_Work"):
        """A preceding, unrelated user transaction, already closed."""
        self.undoInfo(openChunk=True, chunkName=name)
        self.succeed_write("unrelated.translateX", 42)
        self.undoInfo(closeChunk=True)


# All skill scripts that share this helper (issue #607 asks us to exercise
# other callers, not only set_keyframes).
CALLER_CHUNK_NAMES = [
    "dcc_mcp_set_keyframes",
    "dcc_mcp_array_instances",
    "dcc_mcp_lathe_profile",
    "dcc_mcp_loft_sections",
    "dcc_mcp_set_pivot",
    "dcc_mcp_set_skin_weights",
    "dcc_mcp_auto_uv",
]


def test_zero_write_failure_preserves_prior_user_work_and_reports_honest_receipt():
    """The reporter's exact scenario: empty chunk must not undo user work."""
    cmds = FakeUndoQueue()
    cmds.prior_user_work()
    prior_top = cmds.undoInfo(query=True, undoName=True)  # "Previous_User_Work"

    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    # The first write raises BEFORE any scene mutation -> zero recorded writes.
    # (We model the injected failure by simply performing no successful write.)

    receipt = transaction.rollback(lambda: cmds.scene.get("target.translateX") is None)

    # Prior, unrelated user work must be untouched and cmds.undo() never called.
    assert cmds.scene["unrelated.translateX"] == 42
    assert cmds.undo_calls == 0
    assert cmds.undoInfo(query=True, undoName=True) == prior_top
    # The receipt must NOT claim a tool-owned change was verified as undone.
    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False


@pytest.mark.parametrize("chunk_name", CALLER_CHUNK_NAMES)
def test_empty_chunk_never_undoes_prior_work_for_any_shared_helper_caller(chunk_name):
    cmds = FakeUndoQueue()
    cmds.prior_user_work()

    transaction = MayaUndoChunk(cmds, chunk_name)
    transaction.begin()
    receipt = transaction.rollback(lambda: True)

    assert cmds.undo_calls == 0
    assert cmds.scene["unrelated.translateX"] == 42
    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False


def test_partial_write_failure_restores_only_this_invocations_changes():
    """After >=1 recorded writes, undo exactly our own chunk, nothing else."""
    cmds = FakeUndoQueue()
    cmds.prior_user_work()

    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    cmds.succeed_write("targetA.translateX", 5)
    cmds.succeed_write("targetB.translateX", 7)
    # A later write fails; go to rollback with our own chunk still holding writes.

    receipt = transaction.rollback(lambda: cmds.scene.get("targetA.translateX") is None)

    assert cmds.undo_calls == 1
    assert cmds.scene.get("targetA.translateX") is None
    assert cmds.scene.get("targetB.translateX") is None
    # Unrelated prior user work is preserved.
    assert cmds.scene["unrelated.translateX"] == 42
    assert receipt["rollback_attempted"] is True
    assert receipt["rollback_verified"] is True


def test_empty_transaction_with_no_prior_undo_item_makes_no_spurious_undo():
    cmds = FakeUndoQueue()  # empty undo queue

    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    receipt = transaction.rollback(lambda: True)

    assert cmds.undo_calls == 0
    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False


def test_interleaved_foreign_undo_item_blocks_rollback_and_false_success():
    """If the top undo item is not our chunk, refuse to undo and stay honest."""
    cmds = FakeUndoQueue()
    cmds.prior_user_work()

    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    cmds.succeed_write("targetA.translateX", 5)
    # A foreign edit interleaves on top of our chunk before the rollback check.
    cmds.foreign_after_next_close = "Foreign_Interleaved_Edit"

    receipt = transaction.rollback(lambda: False)

    assert cmds.undo_calls == 0
    assert cmds.undoInfo(query=True, undoName=True) == "Foreign_Interleaved_Edit"
    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False


def test_successful_transaction_commits_without_undo():
    cmds = FakeUndoQueue()
    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    cmds.succeed_write("targetA.translateX", 5)
    transaction.commit()

    assert cmds.undo_calls == 0
    assert cmds.scene["targetA.translateX"] == 5


def test_nested_chunk_never_undoes_foreign_outer_transaction():
    """A re-entrant chunk is merged into its outer owner, so we must not undo."""
    cmds = FakeUndoQueue()
    cmds.undoInfo(openChunk=True, chunkName="Outer_User_Macro")
    cmds.succeed_write("unrelated.translateX", 42)

    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    cmds.succeed_write("targetA.translateX", 5)
    receipt = transaction.rollback(lambda: True)

    assert cmds.undoInfo(query=True, undoName=True) == "Outer_User_Macro"
    assert cmds.undo_calls == 0
    assert cmds.scene["unrelated.translateX"] == 42
    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False


def test_host_that_cannot_report_undo_names_fails_closed_without_undo():
    """Unprovable ownership must never turn into an optimistic undo."""
    cmds = FakeUndoQueue()
    cmds.prior_user_work()
    cmds.raise_on_undo_name_query = True

    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    cmds.succeed_write("targetA.translateX", 5)
    receipt = transaction.rollback(lambda: True)

    assert cmds.undo_calls == 0
    assert cmds.scene["unrelated.translateX"] == 42
    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False
    assert receipt["rollback_skipped_reason"] == "undo_item_not_owned"


def test_cancelled_zero_write_transaction_never_undoes_prior_user_work():
    """Cancellation before the first write is just another empty chunk."""
    cmds = FakeUndoQueue()
    cmds.prior_user_work()

    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")
    transaction.begin()
    # Cancelled: rollback is requested with a verifier that would wrongly
    # report success, but no undoable write was ever recorded.
    receipt = transaction.rollback(lambda: True)

    assert cmds.undo_calls == 0
    assert cmds.scene["unrelated.translateX"] == 42
    assert receipt["rollback_attempted"] is False
    assert receipt["rollback_verified"] is False


def test_undo_disabled_still_refuses_at_begin():
    cmds = FakeUndoQueue()
    cmds.undo_enabled = False
    transaction = MayaUndoChunk(cmds, "dcc_mcp_set_keyframes")

    with pytest.raises(RuntimeError, match="undo must be enabled"):
        transaction.begin()
    assert cmds.undo_calls == 0
