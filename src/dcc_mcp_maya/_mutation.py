"""Small fail-closed helpers for verified Maya scene mutations."""

from __future__ import annotations

# Import built-in modules
import uuid


def node_uuid(cmds, node):
    # type: (...) -> str
    """Return the one exact Maya UUID for ``node`` or fail closed."""
    values = [str(value) for value in (cmds.ls(node, uuid=True) or [])]
    if len(values) != 1 or not values[0]:
        raise RuntimeError("Maya did not return one exact node UUID")
    return values[0]


def uuid_inventory(cmds):
    # type: (...) -> set
    """Snapshot all Maya UUIDs for exact creation and rollback proofs."""
    return {str(value) for value in (cmds.ls(uuid=True) or [])}


def shape_uuids(cmds, transform):
    # type: (...) -> set
    """Return UUIDs for the transform's non-intermediate shapes."""
    shapes = cmds.listRelatives(transform, shapes=True, noIntermediate=True, fullPath=True) or []
    return {node_uuid(cmds, shape) for shape in shapes}


class MayaUndoChunk:
    """Own one Maya undo chunk and emit a structured rollback receipt.

    A chunk is *open* as soon as :meth:`begin` calls
    ``undoInfo(openChunk=True)``, but Maya only records an undo item when at
    least one undoable command actually ran inside it. Undoing an empty chunk
    pops the preceding, unrelated user transaction (issue #607), while the
    caller's verifier only checks the tool's own target curves and therefore
    reports a false ``rollback_verified=true``.

    To prove ownership, every chunk gets a unique name. Before undoing, the
    helper compares Maya's top undo item (``undoInfo(query=True,
    undoName=True)``) to that name. Only an exact match proves the top item is
    this invocation's chunk; an empty chunk, a foreign interleaved edit, or a
    host that cannot report undo names all fail closed: nothing is undone and
    the receipt never claims a verified rollback.
    """

    def __init__(self, cmds, name):
        # type: (...) -> None
        self._cmds = cmds
        self._name = name
        # Unique per-invocation identity so an unrelated chunk that happens to
        # share the human-readable name can never be mistaken for ours.
        self._chunk_name = "{}__{}".format(name, uuid.uuid4().hex)
        self._open = False

    def begin(self):
        # type: (...) -> None
        if not bool(self._cmds.undoInfo(query=True, state=True)):
            raise RuntimeError("Maya undo must be enabled for this verified mutation")
        self._cmds.undoInfo(openChunk=True, chunkName=self._chunk_name)
        self._open = True

    def _close(self):
        # type: (...) -> None
        if self._open:
            self._cmds.undoInfo(closeChunk=True)
            self._open = False

    def commit(self):
        # type: (...) -> None
        self._close()

    def _owns_top_undo_item(self):
        # type: (...) -> bool
        """Return True only when Maya's top undo item is provably ours.

        Fails closed on any error or ambiguity. A non-string answer (for
        example from a host that does not expose undo names) is never accepted
        as proof of ownership.
        """
        try:
            top = self._cmds.undoInfo(query=True, undoName=True)
        except Exception:  # noqa: BLE001 - fail closed on any query failure
            return False
        return isinstance(top, str) and top == self._chunk_name

    def rollback(self, verifier):
        # type: (...) -> dict
        """Undo *our* chunk only, and verify the caller's pre-state contract.

        When ownership of the top undo item cannot be proven, no ``undo()`` is
        issued (prior user history is left untouched) and the receipt reports
        an honest, unverified outcome instead of a false success.
        """
        receipt = {
            "rollback_attempted": False,
            "rollback_verified": False,
        }
        try:
            self._close()
            if not self._owns_top_undo_item():
                # Empty or unprovable transaction: never undo unrelated work.
                receipt["rollback_skipped_reason"] = "undo_item_not_owned"
                return receipt
            receipt["rollback_attempted"] = True
            self._cmds.undo()
            receipt["rollback_verified"] = bool(verifier())
        except Exception as exc:  # noqa: BLE001 - never leak local scene detail
            receipt["rollback_verified"] = False
            receipt["rollback_error_type"] = type(exc).__name__
        return receipt
