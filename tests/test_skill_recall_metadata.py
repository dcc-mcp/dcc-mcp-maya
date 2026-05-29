"""Recall-metadata regression tests for bundled Maya skills (issue #308).

These pin the structured metadata the gateway / core retrieval layer relies on
to pick the right skill *without* depending only on generated script names:

1. Every bundled skill declares both an intent ``layer`` and a workflow
   ``stage`` in its ``SKILL.md`` frontmatter.
2. The arbitrary-execution escape hatch (``execute_python`` / ``execute_mel``)
   lives in a ``thin-harness`` / ``bootstrap`` skill so core's layer ranking
   keeps it *below* typed domain skills for normal workflows.
3. Common natural-language queries resolve to the right typed skill through
   ``search-hint`` aliases + ``tags`` (not just exact tool names).
4. Destructive tools carry a ``destructive_hint`` side-effect annotation.

All checks read the bundled files directly and need no running Maya.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "src" / "dcc_mcp_maya" / "skills"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _skill_dirs() -> List[Path]:
    return sorted(p.parent for p in SKILLS_DIR.glob("*/SKILL.md"))


def _frontmatter(skill_dir: Path) -> Dict:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    assert match, "{} missing frontmatter".format(skill_dir)
    data = yaml.safe_load(match.group(1)) or {}
    return data.get("metadata", {}).get("dcc-mcp", {})


def _searchable_text(skill_dir: Path) -> str:
    meta = _frontmatter(skill_dir)
    parts = [skill_dir.name]
    parts.extend(str(t) for t in meta.get("tags", []) or [])
    parts.append(str(meta.get("search-hint", "")))
    return " ".join(parts).lower()


def _skills_matching(tokens: List[str], exclude_bootstrap: bool = True) -> Set[str]:
    """Return skills whose searchable text contains *all* tokens."""
    out: Set[str] = set()
    for skill_dir in _skill_dirs():
        meta = _frontmatter(skill_dir)
        if exclude_bootstrap and meta.get("stage") == "bootstrap":
            continue
        text = _searchable_text(skill_dir)
        if all(tok in text for tok in tokens):
            out.add(skill_dir.name)
    return out


def _bundled_tools():
    for tools_yaml in sorted(SKILLS_DIR.glob("*/tools.yaml")):
        data = yaml.safe_load(tools_yaml.read_text(encoding="utf-8")) or {}
        for tool in data.get("tools", []):
            yield tools_yaml.parent.name, tool


# ---------------------------------------------------------------------------
# Intent + stage metadata completeness
# ---------------------------------------------------------------------------


def test_every_skill_declares_layer_and_stage() -> None:
    for skill_dir in _skill_dirs():
        meta = _frontmatter(skill_dir)
        assert meta.get("layer"), "{} missing metadata.dcc-mcp.layer".format(skill_dir.name)
        assert meta.get("stage"), "{} missing metadata.dcc-mcp.stage".format(skill_dir.name)


# ---------------------------------------------------------------------------
# Escape-hatch ranking (acceptance: execute-python ranks after typed skills)
# ---------------------------------------------------------------------------


def test_arbitrary_execution_tools_live_in_thin_harness_bootstrap() -> None:
    owners = {skill for skill, tool in _bundled_tools() if tool.get("name") in {"execute_python", "execute_mel"}}
    assert owners, "execute_python / execute_mel must exist as the escape hatch"
    for owner in owners:
        meta = _frontmatter(SKILLS_DIR / owner)
        assert meta.get("layer") == "thin-harness", (
            "{} owns execute_python/mel but is not layer 'thin-harness' — core "
            "ranking would let the escape hatch outrank typed skills".format(owner)
        )
        assert meta.get("stage") == "bootstrap", owner


# ---------------------------------------------------------------------------
# Natural-language recall via search-hint aliases + tags
# ---------------------------------------------------------------------------


def test_recall_phrases_resolve_to_typed_skills() -> None:
    # "make an animated rig and playblast"
    assert "maya-render" in _skills_matching(["rig", "playblast"])
    assert "maya-render" in _skills_matching(["playblast"])
    assert _skills_matching(["animat", "rig"])  # animation/animated + rig

    # "export geometry to FBX"
    assert "maya-geometry" in _skills_matching(["export", "fbx"])

    # "create some spheres"
    assert "maya-primitives" in _skills_matching(["create", "sphere"])

    # "build a character rig"
    assert "maya-rigging" in _skills_matching(["character", "rig"])


def test_recall_phrases_do_not_collapse_to_bootstrap_only() -> None:
    """No priority phrase should be served *only* by the escape hatch."""
    for tokens in (["rig", "playblast"], ["export", "fbx"], ["create", "sphere"]):
        typed = _skills_matching(tokens, exclude_bootstrap=True)
        assert typed, "phrase {} has no typed skill match".format(tokens)


# ---------------------------------------------------------------------------
# Side-effect signalling
# ---------------------------------------------------------------------------


def test_destructive_tools_declare_destructive_hint() -> None:
    offenders = []
    for skill, tool in _bundled_tools():
        name = str(tool.get("name", ""))
        if name.startswith("delete"):
            annotations = tool.get("annotations") or {}
            if not annotations.get("destructive_hint"):
                offenders.append("{}:{}".format(skill, name))
    assert offenders == [], "destructive tools missing destructive_hint: {}".format(offenders)
