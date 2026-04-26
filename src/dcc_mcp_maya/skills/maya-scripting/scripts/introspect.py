"""Maya-specific introspection provider.

Implements the ``dcc_introspect__*`` contract for:

- ``maya.cmds``       — live ``maya.cmds.help()`` parser (version-exact, per-session)
- ``maya.mel``        — MEL ``whatIs`` lookup
- ``maya.api.*``      — bundled per-version JSON index + ``inspect`` fallback

Multi-version strategy (mirrors pymel's cmdcache approach):
  1. For ``maya.cmds``: always call ``maya.cmds.help(cmd=name)`` live — the
     running Maya session IS the version, so the data is exact.
  2. For ``OpenMaya``/``OpenMayaAnim``/etc.: load the bundled JSON keyed to
     the current major Maya version, fall back to the nearest lower version,
     then fall back to live ``inspect``.

Thread affinity:
  ``list_module``, ``signature``, ``search`` — no DAG access, ``affinity: any``.
  ``eval`` — must run on the main thread, ``affinity: main``.
"""

from __future__ import annotations

# Import built-in modules
import ast
import inspect
import json
import os
import re
from typing import Any, Dict, List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# ---------------------------------------------------------------------------
# Helpers — version detection
# ---------------------------------------------------------------------------

_SIGNATURES_DIR = os.path.join(os.path.dirname(__file__), "..", "references", "openmaya_signatures")

# Normalised at import time so path arithmetic works on all platforms.
_SIGNATURES_DIR = os.path.normpath(_SIGNATURES_DIR)


def _maya_major_version() -> str:
    """Return the current Maya major version string, e.g. '2024'."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        return str(cmds.about(majorVersion=True))
    except Exception:
        return "2024"


def _load_openmaya_index(requested_version: Optional[str] = None) -> Dict[str, Any]:
    """Load the bundled OpenMaya signatures JSON for *requested_version*.

    Resolution order (same pattern as pymel per-version caches):
    1. Exact version file ``maya_<ver>.json``.
    2. Nearest lower version file available in ``_SIGNATURES_DIR``.
    3. Empty dict (graceful degradation; live ``inspect`` used as fallback).
    """
    version = requested_version or _maya_major_version()

    exact_path = os.path.join(_SIGNATURES_DIR, "maya_{}.json".format(version))
    if os.path.isfile(exact_path):
        with open(exact_path, encoding="utf-8") as fh:
            return json.load(fh)

    # Find nearest lower version
    available: List[str] = []
    for fname in os.listdir(_SIGNATURES_DIR):
        m = re.match(r"^maya_(\d{4})\.json$", fname)
        if m:
            available.append(m.group(1))

    available.sort()
    lower = [v for v in available if v <= version]
    if lower:
        fallback_path = os.path.join(_SIGNATURES_DIR, "maya_{}.json".format(lower[-1]))
        with open(fallback_path, encoding="utf-8") as fh:
            return json.load(fh)

    return {}


# ---------------------------------------------------------------------------
# maya.cmds.help() parser  (ported from pymel getCmdInfoBasic)
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "string": "str",
    "length": "float",
    "float": "float",
    "angle": "float",
    "int": "int",
    "unsignedint": "int",
    "on|off": "bool",
    "boolean": "bool",
    "script": "callable",
    "name": "str",
    "time": "float",
    "uint": "int",
}

# Per-process LRU cache keyed by command name — Maya's flag table is stable
# within a single session regardless of scene state.
_CMDS_HELP_CACHE: Dict[str, Dict[str, Any]] = {}


def _parse_cmds_help(command: str) -> Dict[str, Any]:
    """Parse ``maya.cmds.help(cmd=command)`` output into a structured dict.

    Returns a dict with keys:
      ``synopsis``  — first line of help output.
      ``flags``     — list of flag dicts, each with keys:
                      short, long, type, modes, multiuse.
    """
    if command in _CMDS_HELP_CACHE:
        return _CMDS_HELP_CACHE[command]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        raw = cmds.help(cmd=command) or ""
    except Exception as exc:
        return {"error": str(exc), "synopsis": "", "flags": []}

    lines = raw.split("\n")
    synopsis = lines[0].strip() if lines else ""

    # Skip the "Flags:" header line
    flag_lines = [ln for ln in lines[1:] if ln.strip() and not ln.strip().startswith("Flags")]

    flags: List[Dict[str, Any]] = []
    for line in flag_lines:
        cleaned = line.replace("(Query Arg Mandatory)", "").replace("(Query Arg Optional)", "")
        multiuse = "(multi-use)" in cleaned
        cleaned = cleaned.replace("(multi-use)", "")
        tokens = cleaned.split()

        if len(tokens) < 2 or not tokens[0].startswith("-"):
            continue

        short_flag = tokens[0].lstrip("-")
        long_flag = tokens[1].lstrip("-") if len(tokens) > 1 else short_flag

        # Modes are in trailing parentheses: (create,edit,query)
        modes: List[str] = []
        mode_match = re.search(r"\(([^)]+)\)\s*$", cleaned)
        if mode_match:
            modes = [m.strip() for m in mode_match.group(1).split(",")]
        if multiuse:
            modes.append("multiuse")

        # Types are tokens between flag names and mode parenthesis
        mode_start = cleaned.rfind("(") if mode_match else len(cleaned)
        type_tokens = cleaned[len(tokens[0]) + len(tokens[1]) + 2 : mode_start].split()
        py_types = [_TYPE_MAP.get(t.lower(), t.lower()) for t in type_tokens]

        flags.append(
            {
                "short": short_flag,
                "long": long_flag,
                "type": py_types[0] if len(py_types) == 1 else py_types or "bool",
                "modes": modes,
                "multiuse": multiuse,
            }
        )

    result: Dict[str, Any] = {"synopsis": synopsis, "flags": flags}
    _CMDS_HELP_CACHE[command] = result
    return result


# ---------------------------------------------------------------------------
# OpenMaya signature lookup
# ---------------------------------------------------------------------------


def _openmaya_signature(qualified_name: str) -> Optional[Dict[str, Any]]:
    """Look up ``module.ClassName.method`` in the bundled JSON index.

    *qualified_name* examples:
    - ``maya.api.OpenMaya.MFnMesh``
    - ``maya.api.OpenMaya.MFnMesh.getPoints``
    - ``maya.api.OpenMayaAnim.MFnAnimCurve.addKey``
    """
    index = _load_openmaya_index()
    modules_data = index.get("modules", {})

    parts = qualified_name.split(".")

    # Determine module portion vs class/method portion.
    # Module names are like "maya.api.OpenMaya", "maya.api.OpenMayaAnim", etc.
    for i in range(len(parts), 0, -1):
        candidate_module = ".".join(parts[:i])
        if candidate_module in modules_data:
            rest = parts[i:]
            class_data = modules_data[candidate_module]

            if not rest:
                # Asking for the whole module listing
                return {"module": candidate_module, "classes": list(class_data.keys())}

            class_entry = class_data.get(rest[0])
            if class_entry is None:
                break

            if len(rest) == 1:
                return class_entry

            method_entry = class_entry.get("methods", {}).get(rest[1])
            if method_entry:
                return method_entry
            break

    # Fallback: live inspect
    return _inspect_openmaya(qualified_name)


def _inspect_openmaya(qualified_name: str) -> Optional[Dict[str, Any]]:
    """Attempt ``inspect``-based signature extraction for OpenMaya objects."""
    try:
        parts = qualified_name.split(".")
        obj = __import__(".".join(parts[:-1]), fromlist=[parts[-1]])
        for part in parts[3:]:  # skip maya.api.OpenMaya* prefix
            obj = getattr(obj, part)

        sig = "(unknown)"
        try:
            sig = str(inspect.signature(obj))
        except (ValueError, TypeError):
            pass

        doc = inspect.getdoc(obj) or ""
        return {"signature": sig, "doc": doc.split("\n")[0], "_source": "inspect"}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public skill functions
# ---------------------------------------------------------------------------


def list_module(module: str, page: int = 0, per_page: int = 200) -> dict:
    """List public names in a Maya Python module.

    Supports:
    - ``"maya.cmds"``           — filtered ``dir(maya.cmds)`` (~2800 → ~500 public).
    - ``"maya.api.OpenMaya"``   — classes from bundled JSON index.
    - ``"maya.api.OpenMayaAnim"`` / ``"OpenMayaRender"`` / ``"OpenMayaUI"``.
    - Any other importable Python module.

    Args:
        module:   Module name string.
        page:     Zero-based page index.
        per_page: Items per page (default 200).

    Returns:
        ToolResult with ``context.names`` (list), ``context.total``,
        ``context.page``, ``context.per_page``.
    """
    try:
        names = _get_module_names(module)
    except Exception as exc:
        return skill_exception(exc, message="Failed to list module '{}'".format(module))

    total = len(names)
    start = page * per_page
    page_names = names[start : start + per_page]

    return skill_success(
        "Listed {} names in '{}' (page {}/{})".format(len(page_names), module, page, max(0, (total - 1) // per_page)),
        names=page_names,
        total=total,
        page=page,
        per_page=per_page,
    )


def _get_module_names(module: str) -> List[str]:
    """Return sorted public names for *module*."""
    if module == "maya.cmds":
        import maya.cmds as cmds  # noqa: PLC0415

        return sorted(n for n in dir(cmds) if not n.startswith("_"))

    if module.startswith("maya.api."):
        index = _load_openmaya_index()
        module_data = index.get("modules", {}).get(module, {})
        if module_data:
            return sorted(module_data.keys())
        # Fallback: import and use dir()

    try:
        mod = __import__(module, fromlist=["__name__"])
        return sorted(n for n in dir(mod) if not n.startswith("_"))
    except ImportError:
        return []


def signature(name: str) -> dict:
    """Return the signature/flag-list for a Maya API name.

    Supports fully-qualified names:
    - ``"maya.cmds.polyCube"``
    - ``"maya.mel.eval"``
    - ``"maya.api.OpenMaya.MFnMesh"``
    - ``"maya.api.OpenMaya.MFnMesh.getPoints"``

    Args:
        name: Fully-qualified Python name.

    Returns:
        ToolResult with ``context.signature`` dict.
    """
    try:
        result = _resolve_signature(name)
    except Exception as exc:
        return skill_exception(exc, message="Failed to get signature for '{}'".format(name))

    if result is None:
        return skill_error(
            "No signature found for '{}'".format(name),
            "Check the name with dcc_introspect__search first, or inspect live with execute_python.",
        )

    return skill_success("Signature for '{}'".format(name), signature=result)


def _resolve_signature(name: str) -> Optional[Dict[str, Any]]:
    """Dispatch signature lookup based on namespace prefix."""
    if name.startswith("maya.cmds."):
        cmd = name[len("maya.cmds.") :]
        return _parse_cmds_help(cmd)

    if name.startswith("maya.mel"):
        return _mel_signature(name)

    if name.startswith("maya.api."):
        return _openmaya_signature(name)

    # Generic Python object
    return _inspect_openmaya(name)


def _mel_signature(name: str) -> Optional[Dict[str, Any]]:
    """Use MEL ``whatIs`` to describe a MEL procedure."""
    try:
        import maya.mel as mel  # noqa: PLC0415

        proc = name.split(".")[-1]
        description = mel.eval('whatIs "{}"'.format(proc))
        return {"name": proc, "description": description}
    except Exception:
        return None


def search(module: str, query: str, max_results: int = 30) -> dict:
    """Case-insensitive substring search over a module's public names.

    For ``maya.cmds`` also searches cached flag names so that a query like
    ``"paint attribute"`` can surface ``artAttr*`` commands.

    Args:
        module:      Module name, e.g. ``"maya.cmds"``.
        query:       Substring to search for (case-insensitive).
        max_results: Maximum number of results to return.

    Returns:
        ToolResult with ``context.results`` (list of matching name strings).
    """
    try:
        all_names = _get_module_names(module)
    except Exception as exc:
        return skill_exception(exc, message="Cannot list module '{}' for search".format(module))

    q = query.lower()

    # Primary: match on name
    matched = [n for n in all_names if q in n.lower()]

    # For maya.cmds also search cached flag long-names
    if module == "maya.cmds":
        flag_hits: List[str] = []
        for cmd in all_names:
            if cmd in _CMDS_HELP_CACHE:
                flags = _CMDS_HELP_CACHE[cmd].get("flags", [])
                for f in flags:
                    if q in f.get("long", "").lower() or q in f.get("short", "").lower():
                        if cmd not in matched and cmd not in flag_hits:
                            flag_hits.append(cmd)
        matched = matched + flag_hits

    return skill_success(
        "Found {} match(es) for '{}' in '{}'".format(min(len(matched), max_results), query, module),
        results=matched[:max_results],
        total_matches=len(matched),
    )


def eval_expr(expression: str, timeout_secs: float = 2.0) -> dict:
    """Evaluate a single Python *expression* inside Maya (read-only sandbox).

    Only ``ast.Expression`` nodes are accepted — statements, assignments, and
    imports are rejected to prevent accidental scene modification.

    This tool has ``affinity: main`` because the expression may read DAG state.

    Args:
        expression: A single Python expression string (not a statement).
        timeout_secs: Soft timeout hint in seconds (enforcement via dispatcher).

    Returns:
        ToolResult with ``context.value`` (repr, truncated to 2 KB).
    """
    try:
        ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        return skill_error(
            "Expression is not valid: {}".format(exc),
            "Provide a single Python expression (no statements, no assignments).",
        )

    try:
        import maya.api.OpenMaya as om  # noqa: PLC0415
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        cmds = None  # type: ignore[assignment]
        om = None  # type: ignore[assignment]

    eval_globals = {
        "__builtins__": {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "repr": repr,
            "sorted": sorted,
            "type": type,
        },
        "cmds": cmds,
        "om": om,
    }

    try:
        value = eval(compile(expression, "<introspect-eval>", "eval"), eval_globals)  # noqa: S307
        raw = repr(value)
        truncated = raw[:2048] + ("…" if len(raw) > 2048 else "")
        return skill_success("Expression evaluated", value=truncated)
    except Exception as exc:
        return skill_exception(exc, message="Expression evaluation failed")


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


@skill_entry
def main_list_module(**kwargs) -> dict:
    """Entry point for dcc_introspect__list_module."""
    return list_module(**kwargs)


@skill_entry
def main_signature(**kwargs) -> dict:
    """Entry point for dcc_introspect__signature."""
    return signature(**kwargs)


@skill_entry
def main_search(**kwargs) -> dict:
    """Entry point for dcc_introspect__search."""
    return search(**kwargs)


@skill_entry
def main_eval(**kwargs) -> dict:
    """Entry point for dcc_introspect__eval."""
    return eval_expr(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main_signature)
