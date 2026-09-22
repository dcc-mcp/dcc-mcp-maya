"""Small, typed boundary around Maya's plug-in commands.

The functions accept a ``maya.cmds``-compatible object so the plug-in contract
can be unit tested without importing Maya.  Skill entry points remain
responsible for lazy host imports and result-envelope handling.

Everything here was verified against Maya 2025. Three behaviours drive the
design and are invisible under a fake ``cmds``:

* ``pluginInfo`` metadata flags (``path``, ``version``, ``vendor``,
  ``apiVersion``, ``unloadOk``, ``name``) are only valid **while the plug-in is
  loaded**. Querying them for an unloaded plug-in raises, so they must be read
  opportunistically and reported as unavailable with a reason, never as a
  failure of the whole call.
* ``pluginInfo`` has **no** dependency flag. Asking for one is a dead end;
  dependencies are inferred from the plug-in search path instead.
* ``cmds.loadPlugin(..., quiet=True)`` still **raises** when the plug-in cannot
  be found - ``quiet`` does not suppress load errors. A failed load is therefore
  always an error, and the message is the actionable part.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

#: Environment variable holding the plug-in search path.
PLUGIN_PATH_ENV = "MAYA_PLUG_IN_PATH"

#: ``pluginInfo`` query flags that only work while the plug-in is loaded.
#: Verified on Maya 2025: querying these for an unloaded plug-in raises.
LOADED_ONLY_FLAGS: Tuple[str, ...] = ("path", "version", "vendor", "apiVersion", "unloadOk", "name")

#: ``pluginInfo`` query flags valid whether or not the plug-in is loaded.
ALWAYS_VALID_FLAGS: Tuple[str, ...] = ("loaded", "autoload", "registered")

#: Plug-in file extensions by platform, used to resolve a bare plug-in name to
#: an actual file on the search path.
PLUGIN_EXTENSIONS: Tuple[str, ...] = (".mll", ".bundle", ".so", ".py")


class PluginContractError(ValueError):
    """Raised when a plug-in operation is malformed or cannot be completed."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require(value: str, what: str) -> str:
    name = str(value or "").strip()
    if not name:
        raise PluginContractError("{} must be a non-empty plug-in name".format(what))
    return name


def _query(cmds: Any, plugin: str, flag: str) -> Tuple[bool, Any]:
    """Query one ``pluginInfo`` flag, returning ``(ok, value)``.

    Never raises: an unreadable flag is reported so the caller can explain why
    the metadata is missing instead of failing the whole inspection.
    """
    try:
        return True, cmds.pluginInfo(plugin, query=True, **{flag: True})
    except Exception:  # noqa: BLE001 - a rejected flag is a reportable state
        return False, None


# ---------------------------------------------------------------------------
# Search path
# ---------------------------------------------------------------------------


def _read_env(name: str) -> str:
    """Read an environment variable, preferring Maya's own view of it.

    ``os.environ`` is populated with ``MAYA_PLUG_IN_PATH`` under a running
    Maya (verified on 2025), but a hosted interpreter that inherits a partial
    environment may not have it. MEL ``getenv`` reads the same value from the
    Maya process itself, so it is used as the fallback.
    """
    raw = os.environ.get(name, "") or ""
    if raw:
        return raw
    try:
        import maya.mel as mel  # noqa: PLC0415 - optional host import

        return str(mel.eval('getenv "{}";'.format(name)) or "")
    except Exception:  # noqa: BLE001 - no Maya process means no fallback
        return ""


def plugin_search_path(cmds: Any = None) -> Dict[str, Any]:
    """Return the plug-in search path, split into individual entries.

    There is no ``cmds.pluginPath`` command and no ``cmds.getenv``; the
    authoritative source is the ``MAYA_PLUG_IN_PATH`` environment variable,
    which MEL exposes via ``getenv``. Verified on Maya 2025.
    """
    raw = _read_env(PLUGIN_PATH_ENV)
    separator = ";" if os.name == "nt" else ":"
    entries = [item for item in raw.split(separator) if item.strip()]
    return {
        "env_var": PLUGIN_PATH_ENV,
        "raw": raw,
        "entries": entries,
        "count": len(entries),
        "missing": [item for item in entries if not os.path.isdir(item)],
    }


def find_plugin_file(name: str, search_path: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Locate a plug-in file on the search path.

    Resolves a bare name (``mtoa``) to an actual file, so a "not found" error
    can say whether the plug-in exists at all or is simply not on the path.

    ``search_path`` accepts a :func:`plugin_search_path` result so callers (and
    tests) can resolve against a known path rather than the ambient machine.
    """
    plugin = _require(name, "plugin")
    path = search_path if search_path is not None else plugin_search_path()
    names = [plugin] + [plugin + ext for ext in PLUGIN_EXTENSIONS]
    candidates: List[str] = []
    for directory in path["entries"]:
        if not os.path.isdir(directory):
            continue
        for suffix in names:
            candidate = os.path.join(directory, suffix)
            if os.path.isfile(candidate) and candidate not in candidates:
                candidates.append(candidate)
    return {
        "plugin": plugin,
        "found": bool(candidates),
        "candidates": candidates,
        "searched": path["count"],
        "missing_dirs": path["missing"],
    }


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------


def plugin_record(cmds: Any, plugin: str) -> Dict[str, Any]:
    """Build one plug-in's record, reporting unreadable metadata explicitly.

    Metadata flags only answer while the plug-in is loaded, so an unloaded
    plug-in yields ``available: False`` plus a reason rather than a failure.
    """
    name = _require(plugin, "plugin")
    record: Dict[str, Any] = {"name": name}
    unavailable: List[str] = []

    for flag in ALWAYS_VALID_FLAGS:
        ok, value = _query(cmds, name, flag)
        record[flag] = bool(value) if ok else None
        if not ok:
            unavailable.append(flag)

    loaded = bool(record.get("loaded"))
    for flag in LOADED_ONLY_FLAGS:
        if not loaded:
            record[flag] = None
            unavailable.append(flag)
            continue
        ok, value = _query(cmds, name, flag)
        record[flag] = value if ok else None
        if not ok:
            unavailable.append(flag)

    record["loaded"] = loaded
    record["metadata_available"] = loaded and not unavailable
    record["unavailable_flags"] = sorted(set(unavailable))
    if not loaded:
        record["reason"] = (
            "Plug-in is not loaded; version, path, vendor and API version are only "
            "reported for loaded plug-ins. Load it to inspect its metadata."
        )
    return record


def list_plugins(
    cmds: Any,
    pattern: str = "",
    loaded_only: bool = False,
    limit: int = 200,
) -> Dict[str, Any]:
    """List plug-ins known to Maya, newest-style metadata included."""
    raw = cmds.pluginInfo(query=True, listPlugins=True) or []
    names = sorted(str(item) for item in raw)
    needle = str(pattern or "").strip().lower()
    if needle:
        names = [item for item in names if needle in item.lower()]

    records = [plugin_record(cmds, item) for item in names]
    if loaded_only:
        records = [item for item in records if item["loaded"]]

    max_count = max(1, int(limit))
    selected = records[:max_count]
    return {
        "plugins": selected,
        "count": len(selected),
        "total_matches": len(records),
        "truncated": len(records) > len(selected),
        "pattern": str(pattern or ""),
        "loaded_only": bool(loaded_only),
        "loaded_count": sum(1 for item in records if item["loaded"]),
    }


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_plugin(cmds: Any, plugin: str, autoload: bool = False) -> Dict[str, Any]:
    """Load a plug-in, turning a "not found" into an actionable error.

    ``quiet=True`` does not suppress load errors - Maya still raises - so the
    exception message is the actionable part and is surfaced verbatim.
    """
    name = _require(plugin, "plugin")
    before = bool(cmds.pluginInfo(name, query=True, loaded=True)) if _known(cmds, name) else False

    try:
        result = cmds.loadPlugin(name, quiet=True)
    except Exception as exc:  # noqa: BLE001 - the message is the diagnosis
        located = find_plugin_file(name, search_path=plugin_search_path())
        detail = str(exc).strip() or "plug-in could not be loaded"
        hint = (
            "The plug-in file was found at {} but failed to load; it is likely built "
            "for a different Maya version or is missing a dependency.".format(", ".join(located["candidates"][:3]))
            if located["found"]
            else "No file named {} (with any of {}) exists on {}; add its directory to "
            "{} or install the plug-in.".format(name, ", ".join(PLUGIN_EXTENSIONS), PLUGIN_PATH_ENV, PLUGIN_PATH_ENV)
        )
        raise PluginContractError("{}: {} -- {}".format(name, detail, hint)) from exc

    if autoload:
        try:
            cmds.pluginInfo(name, edit=True, autoload=True)
        except Exception as exc:  # noqa: BLE001 - report, do not fail the load
            raise PluginContractError(
                "{} loaded but its autoload preference could not be set: {}".format(name, exc)
            ) from exc

    return {
        "plugin": name,
        "loaded": True,
        "was_loaded": before,
        "autoload": bool(autoload),
        "result": [str(item) for item in result] if isinstance(result, (list, tuple)) else str(result or ""),
        "record": plugin_record(cmds, name),
    }


def _known(cmds: Any, plugin: str) -> bool:
    """Whether Maya knows about ``plugin`` at all."""
    try:
        names = {str(item) for item in (cmds.pluginInfo(query=True, listPlugins=True) or [])}
    except Exception:  # noqa: BLE001 - treat as unknown
        return False
    return plugin in names


def unload_plugin(cmds: Any, plugin: str, force: bool = False) -> Dict[str, Any]:
    """Unload a plug-in, refusing when Maya reports it cannot be unloaded."""
    name = _require(plugin, "plugin")
    if not _known(cmds, name):
        # Maya drops a plug-in from listPlugins once it is unloaded, so an
        # already-unloaded plug-in also lands here. Say which case it is.
        if find_plugin_file(name, search_path=plugin_search_path())["found"]:
            raise PluginContractError(
                "{} is already unloaded, so there is nothing to unload. Loading it again "
                "would register it with Maya.".format(name)
            )
        raise PluginContractError(
            "Maya does not know a plug-in named {}. Known plug-ins can be listed with list_plugins.".format(name)
        )
    if not bool(cmds.pluginInfo(name, query=True, loaded=True)):
        raise PluginContractError("{} is not loaded, so there is nothing to unload.".format(name))

    ok, unload_ok = _query(cmds, name, "unloadOk")
    if ok and unload_ok is False and not force:
        raise PluginContractError(
            "{} reports it cannot be unloaded (unloadOk=False); another plug-in or the "
            "scene depends on it. Pass force=true to attempt it anyway.".format(name)
        )

    try:
        cmds.unloadPlugin(name, force=bool(force))
    except Exception as exc:  # noqa: BLE001 - surface Maya's reason
        raise PluginContractError("{}: {}".format(name, str(exc).strip())) from exc

    return {"plugin": name, "loaded": False, "forced": bool(force)}


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------


def diagnose_plugin(cmds: Any, plugin: str, search_path: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Report why a plug-in is or is not usable.

    Combines the three signals that matter: is the file on the search path, is
    it loaded, and does Maya consider it registered. Each carries the reason it
    is unavailable so an agent can act on it without a second round trip.
    """
    name = _require(plugin, "plugin")
    search = search_path if search_path is not None else plugin_search_path()
    located = find_plugin_file(name, search_path=search)
    known = _known(cmds, name)
    record = plugin_record(cmds, name) if known else None

    problems: List[str] = []
    suggestions: List[str] = []

    if not known and not located["found"]:
        problems.append(
            "Maya does not know this plug-in and no file named {} exists on {}.".format(name, PLUGIN_PATH_ENV)
        )
        suggestions.append(
            "Install the plug-in, or add its directory to {} ({} entries searched).".format(
                PLUGIN_PATH_ENV, located["searched"]
            )
        )
    elif not known:
        problems.append(
            "A file exists at {} but Maya has not registered it.".format(", ".join(located["candidates"][:3]))
        )
        suggestions.append("Load it once to register it, or check it was built for this Maya version.")
    elif record is not None and not record["loaded"]:
        problems.append("The plug-in is registered but not loaded.")
        suggestions.append("Load it to use its commands, nodes and metadata.")

    # Stale search-path directories are environment hygiene, not a verdict on
    # this plug-in. They are reported as ``warnings`` so ``healthy`` keeps
    # meaning "this plug-in has no problem of its own" - otherwise a perfectly
    # usable plug-in looked unhealthy on any machine with a stale path entry.
    warnings: List[str] = []
    if located["missing_dirs"]:
        warnings.append(
            "{} {} entr{} do not exist.".format(
                len(located["missing_dirs"]),
                PLUGIN_PATH_ENV,
                "y" if len(located["missing_dirs"]) == 1 else "ies",
            )
        )
        suggestions.append("Remove or fix the stale entries in {}.".format(PLUGIN_PATH_ENV))

    return {
        "plugin": name,
        "known": known,
        "loaded": bool(record["loaded"]) if record else False,
        "registered": bool(record["registered"]) if record else False,
        "file_found": located["found"],
        "candidates": located["candidates"],
        "record": record,
        "search_path": search,
        "problems": problems,
        "warnings": warnings,
        "suggestions": suggestions,
        "healthy": not problems,
    }
