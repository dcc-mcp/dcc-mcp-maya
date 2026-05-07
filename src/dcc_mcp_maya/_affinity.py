"""Per-action thread-affinity resolution for Maya skills.

``dcc-mcp-core``'s registry currently does not propagate the
``tools.yaml`` ``affinity`` field to ``registry.get_action(...)``, so
this adapter must read it directly from the skill's ``tools.yaml``
sibling file.

Why this matters
----------------
A skill tagged ``affinity: any`` (pure filesystem / no ``maya.cmds``
access — e.g. ``introspect_list_module``, ``introspect_signature``,
``introspect_search``) can safely run on the calling HTTP worker thread
instead of being serialised behind the Maya UI thread.  Routing every
action through the UI dispatcher regardless of affinity:

1. Wastes a main-thread tick that viewport / user interaction needs.
2. Increases tail latency for concurrent read-only tool calls.
3. Is semantically wrong — the contract is documented in
   ``AGENTS.md`` but the adapter never honoured it.

Design (SOLID)
--------------
* **Single responsibility** — this module only *reads* affinity; it
  does not decide how to execute.  :mod:`_executor` owns dispatch.
* **Open / closed** — new YAML fields can be added without changing
  the public surface (``resolve_affinity`` returns a single string).
* **Interface segregation** — the executor only depends on
  :func:`resolve_affinity`; tests can monkey-patch a single symbol.
* **Dependency inversion** — a custom ``_loader`` can be injected for
  testing to bypass filesystem I/O.

Safe defaults
-------------
When ``tools.yaml`` is missing, malformed, or does not list the tool,
we fall back to ``"main"`` because anything touching ``maya.cmds``
requires the UI thread.  Mis-declaring a Maya-touching action as
``any`` would crash Maya; mis-declaring a pure action as ``main``
merely loses the optimisation, so ``main`` is the Hippocratic choice.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import threading
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

#: Default when ``tools.yaml`` cannot be resolved or parsed.
DEFAULT_AFFINITY: str = "main"

#: Valid affinity values per the ``tools.yaml`` v0.15+ contract.
VALID_AFFINITIES = frozenset({"main", "any"})

# Cache by ``source_file`` absolute path.  Thread-safe because writes
# are idempotent — we always compute the same value for a given path
# and the cache is only a latency optimisation.
_CACHE: Dict[str, str] = {}
_CACHE_LOCK = threading.Lock()

# Optional injectable loader for tests.  Signature: ``(skill_root:str) -> dict``.
_YamlLoader = Callable[[str], Optional[dict]]


def _default_yaml_loader(skill_root: str) -> Optional[dict]:
    """Load ``<skill_root>/tools.yaml`` and return the parsed mapping.

    Returns ``None`` on any error (missing file, parse failure, etc.)
    so :func:`resolve_affinity` can fall through to the safe default.
    """
    tools_yaml = os.path.join(skill_root, "tools.yaml")
    if not os.path.isfile(tools_yaml):
        return None
    try:
        # Import inside the function so unit tests can monkey-patch the
        # YAML loader without importing PyYAML at module import time.
        import yaml  # noqa: PLC0415
    except ImportError:
        logger.debug("PyYAML not available; affinity resolution disabled")
        return None

    try:
        with open(tools_yaml, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:  # noqa: BLE001
        logger.debug("Failed to parse %s: %s", tools_yaml, exc)
        return None

    return data if isinstance(data, dict) else None


def _derive_skill_root(source_file: str) -> Optional[str]:
    """Derive the skill root directory from a script's ``source_file``.

    The expected layout is ``<skill_root>/scripts/<tool_name>.py``.
    Returns ``None`` when the layout does not match so the caller can
    fall back to the default affinity.
    """
    scripts_dir = os.path.dirname(source_file)
    if os.path.basename(scripts_dir).lower() != "scripts":
        return None
    return os.path.dirname(scripts_dir)


def _extract_affinity(tools_yaml: dict, tool_name: str) -> Optional[str]:
    """Return the declared affinity for *tool_name* or ``None``.

    ``tool_name`` here is the ``tools.yaml`` ``name`` field (the script
    stem, e.g. ``introspect_search``), not the fully-qualified
    ``maya_scripting__introspect_search`` action name.
    """
    tools = tools_yaml.get("tools")
    if not isinstance(tools, list):
        return None
    for entry in tools:
        if not isinstance(entry, dict):
            continue
        if entry.get("name") != tool_name:
            continue
        raw = entry.get("affinity")
        if isinstance(raw, str):
            affinity = raw.strip().lower()
            if affinity in VALID_AFFINITIES:
                return affinity
            logger.debug(
                "tools.yaml entry %r declares unknown affinity %r; falling back to default",
                tool_name,
                raw,
            )
        return None
    return None


def resolve_affinity(
    source_file: Optional[str],
    *,
    loader: Optional[_YamlLoader] = None,
) -> str:
    """Return the effective thread affinity for *source_file*.

    Parameters
    ----------
    source_file:
        Absolute path to the skill script (``action["source_file"]``
        as returned by ``registry.get_action``).  May be ``None`` or
        empty when the registry entry is synthetic — the default is
        returned in that case.
    loader:
        Optional YAML loader override for tests.  Must accept a
        ``skill_root`` path and return a parsed mapping or ``None``.

    Returns
    -------
    str
        Either ``"main"`` or ``"any"``.  Never raises — resolution
        failures always degrade to :data:`DEFAULT_AFFINITY`.
    """
    if not source_file:
        return DEFAULT_AFFINITY

    cache_key = os.path.normcase(os.path.abspath(source_file))
    if loader is None:
        with _CACHE_LOCK:
            cached = _CACHE.get(cache_key)
        if cached is not None:
            return cached

    skill_root = _derive_skill_root(source_file)
    if skill_root is None:
        return _remember(cache_key, DEFAULT_AFFINITY, use_cache=loader is None)

    tools_yaml = (loader or _default_yaml_loader)(skill_root)
    if not tools_yaml:
        return _remember(cache_key, DEFAULT_AFFINITY, use_cache=loader is None)

    tool_name = os.path.splitext(os.path.basename(source_file))[0]
    affinity = _extract_affinity(tools_yaml, tool_name) or DEFAULT_AFFINITY
    return _remember(cache_key, affinity, use_cache=loader is None)


def _remember(cache_key: str, value: str, *, use_cache: bool) -> str:
    if use_cache:
        with _CACHE_LOCK:
            _CACHE[cache_key] = value
    return value


def clear_cache() -> None:
    """Drop cached affinity lookups (useful after hot-reload / tests)."""
    with _CACHE_LOCK:
        _CACHE.clear()
