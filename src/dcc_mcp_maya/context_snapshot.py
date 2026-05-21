"""Maya context snapshot provider for gateway routing and REST `/v1/context`.

This module delivers the SOLID collaborators that feed Maya-specific context
into core's post-tool `append_context_snapshot` helper and into
`DccServerBase.update_gateway_metadata`, which together surface live scene
state (open file, selection, display name, version) through:

* the gateway registry (used by `list_dcc_instances`), and
* the per-DCC `GET /v1/context` REST endpoint.

Design
------

* :class:`MayaContextSnapshotProvider` is a callable that returns a fresh
  context dict on every invocation. It is intentionally **small**, **pure**,
  and tolerant of missing Maya: in standalone / headless / subprocess
  contexts it returns a minimal stub instead of crashing.

* :func:`collect_gateway_metadata` returns the subset consumed by
  :meth:`DccServerBase.update_gateway_metadata` (scene / version /
  documents / display_name). It is used after ``load_skill`` / ``unload_skill``
  calls to force the FileRegistry heartbeat to publish the new capability
  state sooner than the next 5-second tick would.

Both helpers obey the *Single Responsibility* rule — they only collect state.
They never mutate Maya, and they never raise: network/gateway I/O stays in
:mod:`dcc_mcp_maya.server`.

Usage::

    provider = MayaContextSnapshotProvider()
    server.set_context_snapshot_provider(provider)

See: https://github.com/loonghao/dcc-mcp-maya/issues/163
     https://github.com/loonghao/dcc-mcp-maya/issues/165
"""

from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "MayaContextSnapshotProvider",
    "collect_gateway_metadata",
    "make_snapshot_provider",
]


# ---------------------------------------------------------------------------
# Snapshot provider
# ---------------------------------------------------------------------------


class MayaContextSnapshotProvider:
    """Callable that returns a fresh Maya context snapshot.

    The provider is designed to be registered with
    :meth:`dcc_mcp_core.server_base.DccServerBase.set_context_snapshot_provider`
    so the core post-tool wrapper can append ``context.maya`` to every result
    envelope — and so the Rust REST layer (`GET /v1/context`) reflects live
    scene state.

    The class follows Interface Segregation: callers only require ``__call__``,
    but a discrete :meth:`collect` method is provided for direct use by
    :class:`MayaMcpServer` when it needs the same state for gateway metadata.

    Parameters
    ----------
    cmds_provider:
        Optional factory returning ``maya.cmds`` (or a duck-typed stand-in
        for tests).  Defaults to a lazy import of ``maya.cmds`` with a
        headless-safe fallback.
    """

    def __init__(
        self,
        cmds_provider: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._cmds_provider = cmds_provider or _default_cmds_provider

    # ------------------------------------------------------------------ API

    def __call__(self) -> Dict[str, Any]:
        return self.collect()

    def collect(self) -> Dict[str, Any]:
        """Return a fresh context snapshot dict.

        Keys (all optional — omitted when unavailable)::

            {
                "dcc":            "maya",
                "scene":          "/path/to/current.ma",
                "scene_modified": True | False,
                "selection":      ["pSphere1", ...],
                "frame":          1001,
                "frame_range":    [1001, 1100],
                "up_axis":        "y" | "z",
                "units":          "cm",
                "display_name":   "Maya — scene.ma",
                "version":        "2025",
                "pid":            12345,
                "available":      True | False,
            }

        The method never raises; Maya-specific probes are guarded so headless
        / standalone contexts return ``{"dcc": "maya", "available": False}``.
        """
        snapshot: Dict[str, Any] = {
            "dcc": "maya",
            "pid": os.getpid(),
            "available": False,
        }

        cmds = self._safe_cmds()
        if cmds is None:
            _attach_recovery_status(snapshot)
            return snapshot

        snapshot["available"] = True

        # Scene path ---------------------------------------------------------
        scene = _safe_call(cmds, "file", q=True, sceneName=True)
        if scene:
            snapshot["scene"] = scene

        modified = _safe_call(cmds, "file", q=True, modified=True)
        if modified is not None:
            snapshot["scene_modified"] = bool(modified)

        # Selection ----------------------------------------------------------
        selection = _safe_call(cmds, "ls", sl=True)
        if isinstance(selection, list):
            snapshot["selection"] = list(selection)

        # Timeline -----------------------------------------------------------
        frame = _safe_call(cmds, "currentTime", q=True)
        if frame is not None:
            try:
                snapshot["frame"] = int(frame)
            except (TypeError, ValueError):
                pass

        start = _safe_call(cmds, "playbackOptions", q=True, min=True)
        end = _safe_call(cmds, "playbackOptions", q=True, max=True)
        if start is not None and end is not None:
            try:
                snapshot["frame_range"] = [int(start), int(end)]
            except (TypeError, ValueError):
                pass

        # Units / axes --------------------------------------------------------
        up_axis = _safe_call(cmds, "upAxis", q=True, axis=True)
        if up_axis:
            snapshot["up_axis"] = str(up_axis)

        units = _safe_call(cmds, "currentUnit", q=True, linear=True)
        if units:
            snapshot["units"] = str(units)

        version = _safe_call(cmds, "about", q=True, version=True)
        if version:
            snapshot["version"] = str(version)

        # Display name -------------------------------------------------------
        display = _derive_display_name(snapshot.get("scene"), snapshot.get("version"))
        if display:
            snapshot["display_name"] = display

        _attach_recovery_status(snapshot)
        return snapshot

    # ------------------------------------------------------------ internals

    def _safe_cmds(self) -> Any:
        try:
            return self._cmds_provider()
        except Exception as exc:  # noqa: BLE001
            logger.debug("MayaContextSnapshotProvider: cmds unavailable: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Gateway metadata helper
# ---------------------------------------------------------------------------


def collect_gateway_metadata(
    provider: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Optional[Any]]:
    """Return a subset snapshot suitable for :meth:`update_gateway_metadata`.

    Parameters
    ----------
    provider:
        Snapshot callable; defaults to :class:`MayaContextSnapshotProvider`.

    Returns
    -------
    dict
        Keys: ``scene`` (str | None), ``version`` (str | None),
        ``documents`` (list[str] | None), ``display_name`` (str | None).

        Maya is a single-document DCC, so ``documents`` is set to
        ``[scene]`` if a scene is open, otherwise ``[]``.  This keeps the
        gateway capability-manifest format consistent across DCCs.
    """
    if provider is None:
        provider = MayaContextSnapshotProvider()
    snapshot = provider() or {}
    scene = snapshot.get("scene")
    documents: Optional[List[str]] = [scene] if scene else []
    return {
        "scene": scene if scene else None,
        "version": snapshot.get("version"),
        "documents": documents,
        "display_name": snapshot.get("display_name"),
    }


def make_snapshot_provider(
    cmds_provider: Optional[Callable[[], Any]] = None,
) -> MayaContextSnapshotProvider:
    """Factory for a :class:`MayaContextSnapshotProvider`.

    Exists so tests can inject a fake ``cmds`` without importing the class
    directly.
    """
    return MayaContextSnapshotProvider(cmds_provider=cmds_provider)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _default_cmds_provider() -> Any:
    """Return ``maya.cmds`` when available, else ``None``.

    Importing ``maya.cmds`` from a non-Maya Python raises ``ImportError``,
    which we convert into a ``None`` return so callers get a uniform
    ``cmds is None`` check.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        return cmds
    except Exception:  # noqa: BLE001 — headless / stub Maya installs
        return None


def _safe_call(cmds: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    """Call ``cmds.<name>(*args, **kwargs)`` swallowing any exception."""
    fn = getattr(cmds, name, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — Maya raises RuntimeError often
        logger.debug("MayaContextSnapshot: cmds.%s raised %s", name, exc)
        return None


def _attach_recovery_status(snapshot: Dict[str, Any]) -> None:
    """Merge the latest Qt recovery-dialog status into a snapshot if present."""
    try:
        from dcc_mcp_maya import _recovery_dialog  # noqa: PLC0415

        snapshot.update(_recovery_dialog.current_context_fields())
    except Exception as exc:  # noqa: BLE001
        logger.debug("MayaContextSnapshotProvider: recovery status unavailable: %s", exc)


def _derive_display_name(scene: Optional[str], version: Optional[str]) -> Optional[str]:
    """Produce a human-readable instance label for gateway disambiguation."""
    if scene:
        try:
            basename = os.path.basename(scene) or scene
        except Exception:  # noqa: BLE001
            basename = scene
        if version:
            return "Maya {} — {}".format(version, basename)
        return "Maya — {}".format(basename)
    if version:
        return "Maya {}".format(version)
    return None
