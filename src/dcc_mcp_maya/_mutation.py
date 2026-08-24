"""Small fail-closed helpers for verified Maya scene mutations."""

from __future__ import annotations


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
    """Own one Maya undo chunk and emit a structured rollback receipt."""

    def __init__(self, cmds, name):
        # type: (...) -> None
        self._cmds = cmds
        self._name = name
        self._open = False

    def begin(self):
        # type: (...) -> None
        if not bool(self._cmds.undoInfo(query=True, state=True)):
            raise RuntimeError("Maya undo must be enabled for this verified mutation")
        self._cmds.undoInfo(openChunk=True, chunkName=self._name)
        self._open = True

    def _close(self):
        # type: (...) -> None
        if self._open:
            self._cmds.undoInfo(closeChunk=True)
            self._open = False

    def commit(self):
        # type: (...) -> None
        self._close()

    def rollback(self, verifier):
        # type: (...) -> dict
        """Undo this chunk and verify the caller-provided pre-state contract."""
        error_type = None
        attempted = False
        try:
            if self._open:
                self._close()
                attempted = True
                self._cmds.undo()
            verified = bool(verifier())
        except Exception as exc:
            verified = False
            error_type = type(exc).__name__
        receipt = {
            "rollback_attempted": attempted,
            "rollback_verified": verified,
        }
        if error_type is not None:
            receipt["rollback_error_type"] = error_type
        return receipt
