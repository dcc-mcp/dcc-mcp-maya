"""Generate per-version OpenMaya signature index JSON.

Run this script **inside a real Maya session** (via ``mayapy`` or the Script
Editor) to produce ``maya_<version>.json`` for the bundled index.

Usage (from repo root, with mayapy on PATH)::

    mayapy tools/generate_openmaya_index.py \\
        --output src/dcc_mcp_maya/skills/maya-scripting/references/openmaya_signatures/

Or via justfile::

    just regen-openmaya-index
    just regen-openmaya-index MAYA_VERSION=2025

The script uses the same two-pass strategy as pymel's ``getCmdInfoBasic``:

1. **Pass 1 — ``inspect``**: iterate ``dir(module)``, collect class/method
   signatures from ``inspect.signature`` and ``inspect.getdoc`` where available.
2. **Pass 2 — docstring heuristic**: for C-extension methods where
   ``inspect.signature`` raises ``ValueError``, extract the signature from the
   first line of the docstring (Maya devkit pattern: ``method(args) -> ret``).

The output is a JSON file matching ``references/openmaya_signatures/schema.json``.

Supports: OpenMaya, OpenMayaAnim, OpenMayaRender, OpenMayaUI (maya.api.* namespace).
"""

from __future__ import annotations

# Import built-in modules
import argparse
import datetime
import inspect
import json
import os
import re
import sys
import types

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODULES_TO_INDEX = [
    "maya.api.OpenMaya",
    "maya.api.OpenMayaAnim",
    "maya.api.OpenMayaRender",
    "maya.api.OpenMayaUI",
]

# Regex to parse C-extension style first-line signatures, e.g.:
#   "getPoints(space=4) -> MPointArray"
#   "setPoints(points, space=kWorld) -> None"
_CEXT_SIG_RE = re.compile(r"^(\w+)\(([^)]*)\)\s*(?:->\s*(.+))?$", re.MULTILINE)

# Prefixes / names to skip — internal / undocumented members
_SKIP_PREFIXES = ("__", "_")
_SKIP_NAMES = frozenset({"mro", "kNullObj"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_sig(obj: object) -> str:
    """Return a best-effort signature string for *obj*."""
    try:
        return str(inspect.signature(obj))
    except (ValueError, TypeError):
        pass

    doc = inspect.getdoc(obj) or ""
    # Try to extract from first docstring line (Maya C-extension pattern)
    first_line = doc.split("\n")[0].strip()
    m = _CEXT_SIG_RE.match(first_line)
    if m:
        args_str = m.group(2)
        ret_str  = m.group(3) or "None"
        return "({}) -> {}".format(args_str, ret_str.strip())

    return "(*args, **kwargs)"


def _short_doc(obj: object) -> str:
    """Return the first paragraph of the docstring, stripped."""
    doc = inspect.getdoc(obj) or ""
    # First paragraph = text up to first blank line
    paragraphs = re.split(r"\n\s*\n", doc, maxsplit=1)
    return paragraphs[0].strip().replace("\n", " ")


def _classify_member(cls: type, name: str) -> str:
    """Determine if a class member is a staticmethod, classmethod, or instance method."""
    for klass in inspect.getmro(cls):
        raw = klass.__dict__.get(name)
        if raw is None:
            continue
        if isinstance(raw, staticmethod):
            return "static"
        if isinstance(raw, classmethod):
            return "classmethod"
        return "method"
    return "method"


def _index_class(cls: type) -> dict:
    """Build the ClassEntry dict for a class."""
    bases = [b.__name__ for b in cls.__mro__[1:] if b is not object]

    methods = {}
    constants = {}

    for name in sorted(dir(cls)):
        if name.startswith(_SKIP_PREFIXES) or name in _SKIP_NAMES:
            continue

        try:
            member = getattr(cls, name)
        except AttributeError:
            continue

        if isinstance(member, int):
            # Treat integer class attributes as constants (MSpace.kWorld, etc.)
            constants[name] = {
                "value": member,
                "doc": _short_doc(member) if hasattr(member, "__doc__") else "",
            }
            continue

        if callable(member) or isinstance(member, (staticmethod, classmethod)):
            kind = _classify_member(cls, name)
            entry: dict = {
                "signature": _safe_sig(member),
                "doc": _short_doc(member),
                "version_added": None,
                "version_removed": None,
            }
            if kind == "static":
                entry["is_static"] = True
            elif kind == "classmethod":
                entry["is_class_method"] = True
            methods[name] = entry

    result = {
        "kind": "class",
        "bases": bases,
        "doc": _short_doc(cls),
        "methods": methods,
    }
    if constants:
        result["constants"] = constants
    return result


def _index_module(module_name: str) -> dict:
    """Import and index all public classes in *module_name*."""
    try:
        mod = __import__(module_name, fromlist=["__name__"])
    except ImportError as exc:
        print("  WARNING: cannot import {}: {}".format(module_name, exc), file=sys.stderr)
        return {}

    class_map = {}
    for name in sorted(dir(mod)):
        if name.startswith(_SKIP_PREFIXES):
            continue

        obj = getattr(mod, name, None)
        if obj is None:
            continue

        if isinstance(obj, type):
            print("    Indexing class {} ...".format(name))
            class_map[name] = _index_class(obj)
        elif callable(obj) and not isinstance(obj, types.ModuleType):
            # Top-level functions (rare in OpenMaya, but present)
            class_map[name] = {
                "kind": "function",
                "bases": [],
                "doc": _short_doc(obj),
                "methods": {},
                "signature": _safe_sig(obj),
            }

    return class_map


# ---------------------------------------------------------------------------
# Changelog computation
# ---------------------------------------------------------------------------

def _compute_changelog(new_index: dict, old_path: str) -> dict:
    """Diff *new_index* against *old_path* and return a changelog entry."""
    if not os.path.isfile(old_path):
        return {}

    with open(old_path, encoding="utf-8") as fh:
        old_index = json.load(fh)

    added: list = []
    removed: list = []
    changed: list = []

    new_modules = new_index.get("modules", {})
    old_modules = old_index.get("modules", {})

    for mod_name, new_classes in new_modules.items():
        old_classes = old_modules.get(mod_name, {})
        for cls_name, new_cls in new_classes.items():
            if cls_name not in old_classes:
                added.append("{}.{}".format(mod_name, cls_name))
                continue
            old_cls = old_classes[cls_name]
            new_methods = set(new_cls.get("methods", {}).keys())
            old_methods = set(old_cls.get("methods", {}).keys())
            for m in new_methods - old_methods:
                added.append("{}.{}.{}".format(mod_name, cls_name, m))
            for m in old_methods - new_methods:
                removed.append("{}.{}.{}".format(mod_name, cls_name, m))
            # Detect signature changes
            for m in new_methods & old_methods:
                new_sig = new_cls["methods"][m].get("signature", "")
                old_sig = old_cls["methods"][m].get("signature", "")
                if new_sig != old_sig:
                    changed.append("{}.{}.{}".format(mod_name, cls_name, m))

        for cls_name in set(old_classes.keys()) - set(new_classes.keys()):
            removed.append("{}.{}".format(mod_name, cls_name))

    return {"added": sorted(added), "removed": sorted(removed), "signature_changed": sorted(changed)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", "-o",
        default="src/dcc_mcp_maya/skills/maya-scripting/references/openmaya_signatures/",
        help="Output directory for JSON files.",
    )
    parser.add_argument(
        "--modules", nargs="+", default=MODULES_TO_INDEX,
        help="OpenMaya module names to index.",
    )
    args = parser.parse_args(argv)

    # Detect Maya version
    try:
        import maya.cmds as cmds  # noqa: PLC0415
        maya_version = str(cmds.about(majorVersion=True))
    except Exception:
        print("ERROR: This script must be run inside a Maya session (mayapy or Script Editor).",
              file=sys.stderr)
        sys.exit(1)

    print("Indexing OpenMaya for Maya {} ...".format(maya_version))

    modules_data: dict = {}
    for module_name in args.modules:
        print("  Module: {} ...".format(module_name))
        modules_data[module_name] = _index_module(module_name)
        print("    {} classes/functions indexed.".format(len(modules_data[module_name])))

    out_dir = os.path.abspath(args.output)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "maya_{}.json".format(maya_version))

    new_index = {
        "version": maya_version,
        "generated_by": "tools/generate_openmaya_index.py",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "modules": modules_data,
    }

    # Compute changelog against previous version file (if any)
    prev_versions = sorted(
        re.match(r"maya_(\d{4})\.json$", f).group(1)
        for f in os.listdir(out_dir)
        if re.match(r"maya_(\d{4})\.json$", f)
        and re.match(r"maya_(\d{4})\.json$", f).group(1) < maya_version
    )
    changelog: dict = {}
    if prev_versions:
        prev_path = os.path.join(out_dir, "maya_{}.json".format(prev_versions[-1]))
        print("Computing changelog against Maya {} ...".format(prev_versions[-1]))
        changelog[maya_version] = _compute_changelog(new_index, prev_path)

    # Merge changelog from existing file if present
    if os.path.isfile(out_path):
        with open(out_path, encoding="utf-8") as fh:
            existing = json.load(fh)
        existing_changelog = existing.get("changelog", {})
        existing_changelog.update(changelog)
        changelog = existing_changelog

    new_index["changelog"] = changelog

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(new_index, fh, indent=2, ensure_ascii=False)

    print("\nWrote index to: {}".format(out_path))
    total_classes = sum(len(v) for v in modules_data.values())
    total_methods = sum(
        len(cls.get("methods", {}))
        for mod in modules_data.values()
        for cls in mod.values()
    )
    print("Summary: {} modules, {} classes/functions, {} methods".format(
        len(modules_data), total_classes, total_methods))

    if changelog.get(maya_version):
        cl = changelog[maya_version]
        print("Changelog vs previous: +{} added, -{} removed, ~{} signature changed".format(
            len(cl["added"]), len(cl["removed"]), len(cl["signature_changed"])))


if __name__ == "__main__":
    main()
