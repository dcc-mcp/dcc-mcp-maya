"""Regression tests for the dynamic stage taxonomy + safe-session firewall.

These tests pin three invariants the dcc-mcp-core / dcc-mcp-maya
contract depends on:

1. **Frontmatter is the single source of truth for stage.** Every
   bundled ``SKILL.md`` declares ``metadata.dcc-mcp.stage``;
   ``dcc_mcp_core.parse_skill_md`` parses it into the typed
   :attr:`SkillMetadata.stage` field; ``_skill_loader.skills_for_stage``
   derives the per-stage skill set at runtime from that field. There
   is **no** hand-maintained ``SKILL_STAGE`` shadow table — these
   tests assert that the public API no longer exposes one and that
   the dynamic discovery agrees with a fresh on-disk scan.
2. **Safe-session firewall composes cleanly.** Without Maya available
   it is a no-op; with a stub ``maya.cmds`` injected into ``sys.modules``
   it neutralises every modal-dialog entry point and restores them
   on exit.

Both invariants are dependency-free: the tests do not require Maya or
``mayapy``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "src" / "dcc_mcp_maya" / "skills"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_STAGE_LINE_RE = re.compile(r"^\s*stage:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bundled_skill_dirs() -> List[Path]:
    """Return every bundled skill directory (one ``SKILL.md`` each)."""
    return sorted(p.parent for p in SKILLS_DIR.glob("*/SKILL.md"))


def _read_stage_field(skill_md: Path) -> str:
    """Extract ``metadata.dcc-mcp.stage`` from a SKILL.md frontmatter.

    The file uses YAML frontmatter; we deliberately do not import
    PyYAML so the test stays runnable in any minimal venv.
    """
    text = skill_md.read_text(encoding="utf-8")
    fm_match = _FRONTMATTER_RE.match(text)
    assert fm_match, "{} is missing a YAML frontmatter block".format(skill_md)
    fm = fm_match.group(1)
    stage_match = _STAGE_LINE_RE.search(fm)
    assert stage_match, "{} is missing a 'stage:' field in frontmatter".format(skill_md)
    return stage_match.group(1).strip()


# ---------------------------------------------------------------------------
# Stage taxonomy invariants
# ---------------------------------------------------------------------------


def test_every_skill_dir_has_stage_field() -> None:
    """Every bundled SKILL.md must declare ``metadata.dcc-mcp.stage``."""
    from dcc_mcp_maya._skill_loader import STAGES

    for skill_dir in _bundled_skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        stage = _read_stage_field(skill_md)
        assert stage in STAGES, "{}: stage {!r} is not one of {}".format(skill_md, stage, STAGES)


def test_skills_index_stage_table_matches_disk() -> None:
    """The human-readable skill inventory must match the bundled skill dirs."""
    from dcc_mcp_maya._skill_loader import STAGES

    index_text = (SKILLS_DIR / "SKILLS_INDEX.md").read_text(encoding="utf-8")
    count_match = re.search(r"The (\d+) bundled skills", index_text)
    assert count_match, "SKILLS_INDEX.md must state the bundled skill count"
    assert int(count_match.group(1)) == len(_bundled_skill_dirs())

    on_disk = {stage: set() for stage in STAGES}
    for skill_dir in _bundled_skill_dirs():
        on_disk[_read_stage_field(skill_dir / "SKILL.md")].add(skill_dir.name)

    for stage, expected in on_disk.items():
        row_match = re.search(r"\| `{}` \|[^\n]*\|([^\n]*)\|".format(stage), index_text)
        assert row_match, "SKILLS_INDEX.md is missing stage row {!r}".format(stage)
        documented = set(re.findall(r"`([^`]+)`", row_match.group(1)))
        assert documented == expected, "SKILLS_INDEX.md stage {!r} drift: docs={} disk={}".format(
            stage,
            sorted(documented),
            sorted(expected),
        )


def test_no_hardcoded_skill_stage_dict_exists() -> None:
    """The deprecated ``SKILL_STAGE`` constant must NOT be re-exposed.

    The whole point of moving stage discovery to a dynamic frontmatter
    scan (backed by ``dcc_mcp_core.SkillMetadata.stage``) is that no
    Python file in this repo carries a parallel ``{name → stage}``
    mapping that can drift out of sync with the SKILL.md files. This
    test fails loudly the moment someone reintroduces the shadow
    table — at the module surface or as a top-level package export.
    """
    import dcc_mcp_maya
    from dcc_mcp_maya import _skill_loader

    assert not hasattr(_skill_loader, "SKILL_STAGE"), (
        "_skill_loader.SKILL_STAGE re-introduced — stage data must be "
        "derived from each SKILL.md frontmatter on demand, not from "
        "a hand-maintained dict."
    )
    assert not hasattr(dcc_mcp_maya, "SKILL_STAGE"), (
        "dcc_mcp_maya.SKILL_STAGE re-introduced — see _skill_loader.py docstring for the dynamic alternatives."
    )


def test_no_hardcoded_minimal_deactivate_groups_dict_exists() -> None:
    """The deprecated ``MINIMAL_DEACTIVATE_GROUPS`` constant must NOT
    be re-exposed.

    Each bundled ``groups.yaml`` already declares ``default_active``
    per group; ``_skill_loader._default_minimal_deactivate_groups()``
    derives the deactivation map from that single source of truth.
    Reintroducing a hand-maintained mirror would silently get out of
    sync the next time a skill author flipped a group's default state.
    """
    import dcc_mcp_maya
    from dcc_mcp_maya import _skill_loader

    assert not hasattr(_skill_loader, "MINIMAL_DEACTIVATE_GROUPS"), (
        "_skill_loader.MINIMAL_DEACTIVATE_GROUPS re-introduced — "
        "default-inactive groups must be derived from each skill's "
        "groups.yaml on demand."
    )
    assert not hasattr(dcc_mcp_maya, "MINIMAL_DEACTIVATE_GROUPS"), (
        "dcc_mcp_maya.MINIMAL_DEACTIVATE_GROUPS re-introduced — see "
        "_skill_loader._default_minimal_deactivate_groups() instead."
    )


def test_default_minimal_deactivate_groups_matches_groups_yaml(tmp_path) -> None:
    """``_default_minimal_deactivate_groups`` must project each
    bundled ``groups.yaml`` correctly: every group whose
    ``default_active`` is ``false`` becomes a deactivation entry, and
    every other group is omitted."""
    from dcc_mcp_maya._skill_loader import (
        MINIMAL_SKILLS,
        _default_minimal_deactivate_groups,
        _read_default_inactive_groups,
    )

    derived = _default_minimal_deactivate_groups(MINIMAL_SKILLS)
    for skill_name in MINIMAL_SKILLS:
        skill_dir = SKILLS_DIR / skill_name
        expected = _read_default_inactive_groups(skill_dir)
        if expected:
            assert derived.get(skill_name) == expected, "{} deactivate groups drift: derived={} expected={}".format(
                skill_name,
                derived.get(skill_name),
                expected,
            )
        else:
            assert skill_name not in derived, (
                "{} has no default-inactive groups in groups.yaml but appears in the deactivate map".format(skill_name)
            )

    # Skills NOT in the requested set must never leak into the map —
    # this guards against future regressions where the projection
    # forgets to filter.
    for stray in derived:
        assert stray in MINIMAL_SKILLS, "deactivate map carries entries for skills the caller did not request: " + stray


def test_build_minimal_mode_config_pulls_deactivate_from_groups_yaml() -> None:
    """``build_minimal_mode_config`` must wire the dynamically-derived
    deactivate map into ``MinimalModeConfig.deactivate_groups`` so the
    ``default_active: false`` declarations in each ``groups.yaml`` are
    actually honoured at startup."""
    from dcc_mcp_maya._skill_loader import (
        MINIMAL_SKILLS,
        _default_minimal_deactivate_groups,
        build_minimal_mode_config,
    )

    cfg = build_minimal_mode_config()
    assert cfg.skills == MINIMAL_SKILLS
    expected = _default_minimal_deactivate_groups(MINIMAL_SKILLS)
    # Compare by content; cfg.deactivate_groups is a Mapping (may be
    # any dict-like); copy into a plain dict for an apples-to-apples
    # comparison.
    assert dict(cfg.deactivate_groups) == expected


def test_core_parses_metadata_dcc_mcp_stage_into_typed_field() -> None:
    """``dcc_mcp_core.parse_skill_md`` must populate the typed
    :attr:`SkillMetadata.stage` field for any bundled skill.

    This is the contract Maya relies on — if core stops setting the
    typed field, ``skills_for_stage()`` silently returns empty tuples.
    """
    import dcc_mcp_core

    sample = SKILLS_DIR / "maya-scripting"
    assert (sample / "SKILL.md").is_file(), sample
    meta = dcc_mcp_core.parse_skill_md(str(sample))
    assert meta is not None, "core failed to parse a known-good SKILL.md"
    on_disk_stage = _read_stage_field(sample / "SKILL.md")
    typed_stage = getattr(meta, "stage", None)
    assert typed_stage == on_disk_stage, (
        "core.parse_skill_md(...).stage={!r} disagrees with SKILL.md "
        "frontmatter stage={!r} — the metadata.dcc-mcp.stage parser arm "
        "is not wired through to SkillMetadata.stage".format(typed_stage, on_disk_stage)
    )


def test_skills_for_stage_matches_dynamic_frontmatter_scan() -> None:
    """``skills_for_stage(s)`` must return *exactly* the bundled skills
    whose SKILL.md frontmatter declares ``stage: s``.

    The expected set is computed by re-scanning the SKILL.md files in
    this test (independent of ``_skill_loader``'s own scan), so any
    drift between the helper and the on-disk truth fails the test.
    """
    from dcc_mcp_maya._skill_loader import STAGES, skills_for_stage

    on_disk: Dict[str, str] = {
        skill_dir.name: _read_stage_field(skill_dir / "SKILL.md") for skill_dir in _bundled_skill_dirs()
    }
    for stage in STAGES:
        expected = {name for name, st in on_disk.items() if st == stage}
        actual = set(skills_for_stage(stage))
        assert actual == expected, "skills_for_stage({!r}) drift: helper={} vs on-disk={}".format(
            stage,
            sorted(actual),
            sorted(expected),
        )

    with pytest.raises(ValueError):
        skills_for_stage("not-a-real-stage")


def test_skills_for_stage_ignores_skills_without_stage(tmp_path) -> None:
    """A SKILL.md without ``metadata.dcc-mcp.stage`` must NOT crash the
    helper, and must NOT be returned by any ``skills_for_stage(...)``
    call. We simulate this by pointing the loader at a temp directory
    containing one staged + one un-staged skill."""
    from dcc_mcp_maya import _skill_loader

    # Two skills: one declares stage=authoring, one declares no stage.
    (tmp_path / "with-stage" / "scripts").mkdir(parents=True)
    (tmp_path / "with-stage" / "SKILL.md").write_text(
        "---\n"
        "name: with-stage\n"
        "description: Has a stage tag.\n"
        "metadata:\n"
        "  dcc-mcp:\n"
        "    dcc: maya\n"
        "    stage: authoring\n"
        "---\n",
        encoding="utf-8",
    )
    (tmp_path / "no-stage" / "scripts").mkdir(parents=True)
    (tmp_path / "no-stage" / "SKILL.md").write_text(
        "---\nname: no-stage\ndescription: Has no stage tag.\nmetadata:\n  dcc-mcp:\n    dcc: maya\n---\n",
        encoding="utf-8",
    )

    # Redirect the cached scan at our fixture and clear the cache.
    original_dir = _skill_loader._BUNDLED_SKILLS_DIR
    _skill_loader._BUNDLED_SKILLS_DIR = tmp_path
    _skill_loader._clear_bundled_cache()
    try:
        authoring = _skill_loader.skills_for_stage("authoring")
        assert "with-stage" in authoring
        assert "no-stage" not in authoring
        # Other stages must not see either skill.
        for stage in _skill_loader.STAGES:
            if stage == "authoring":
                continue
            assert _skill_loader.skills_for_stage(stage) == ()
    finally:
        _skill_loader._BUNDLED_SKILLS_DIR = original_dir
        _skill_loader._clear_bundled_cache()


def test_build_minimal_mode_for_stages_always_includes_bootstrap() -> None:
    from dcc_mcp_maya._skill_loader import build_minimal_mode_for_stages

    # User asks only for 'interchange'. Bootstrap must still be present.
    cfg = build_minimal_mode_for_stages(["interchange"])
    assert "maya-scripting" in cfg.skills, cfg.skills
    assert "maya-geometry" in cfg.skills, cfg.skills
    # Authoring is not requested → must not be eagerly loaded.
    assert "maya-mesh-ops" not in cfg.skills, cfg.skills


def test_build_minimal_mode_for_stages_rejects_unknown() -> None:
    from dcc_mcp_maya._skill_loader import build_minimal_mode_for_stages

    with pytest.raises(ValueError):
        build_minimal_mode_for_stages(["not-a-stage"])


# ---------------------------------------------------------------------------
# Safe-session firewall — REMOVED 2026-05-16 (regression guards below)
# ---------------------------------------------------------------------------
#
# `dcc_mcp_maya._safe_session` no longer exists. Three sequential field
# reports forced removal of every responsibility the module used to carry:
#
# 1. `cmds.confirmDialog` / `fileDialog2` monkey-patch crashed Maya on
#    ``cmds.file(new=True)`` + Arnold renderer switch (Maya's C++ side
#    consumed our stub `"dismiss"` value as a state-machine input).
# 2. AutoSave per-job snooze had a between-jobs window where the
#    timer fired and popped Maya's "must give a name" modal — moved
#    to a session-wide persistent disable in
#    `maya/plugin/dcc_mcp_maya_plugin.py::_disable_autosave_for_session`.
# 3. With (1) and (2) gone, `mcp_safe_session` was a no-op
#    context-manager wrapper around every dispatched job; removing it
#    aligns the dispatch path with PatrickPalmer/maya-mcp-server,
#    which never wrapped `cmds.*` calls and is stable on the same
#    user scripts that crashed our adapter.
#
# These tests pin the removal so a future contributor cannot
# accidentally reintroduce the wrapper.


def test_safe_session_module_is_absent() -> None:
    """``dcc_mcp_maya._safe_session`` must not exist as an import target.

    Pins the 2026-05-16 removal. If someone resurrects the module
    (even as an empty shim that re-exports stale names), this test
    fails first so they read the rationale block above.
    """
    with pytest.raises(ImportError):
        import dcc_mcp_maya._safe_session  # noqa: F401


def test_executor_runs_skill_without_safe_session_import() -> None:
    """``run_skill_script`` must not pull in any safe-session symbol.

    Catches the regression where a refactor would re-add the
    ``with mcp_safe_session():`` wrapping around the executor body.
    AST-walks the executor module so the test ignores docstring /
    comment mentions and only fires on real ``import`` statements
    or ``Name`` references in code.
    """
    import ast
    import inspect

    from dcc_mcp_maya import _executor

    tree = ast.parse(inspect.getsource(_executor))

    bad_imports: List[str] = []
    bad_names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.endswith("_safe_session") or "_safe_session" in module.split("."):
                bad_imports.append("from {} import {}".format(module, ", ".join(a.name for a in node.names)))
            for alias in node.names:
                if alias.name == "mcp_safe_session":
                    bad_imports.append("from {} import mcp_safe_session".format(module))
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.endswith("_safe_session") or alias.name == "mcp_safe_session":
                    bad_imports.append("import {}".format(alias.name))
        if isinstance(node, ast.Name) and node.id == "mcp_safe_session":
            bad_names.append("Name reference at line {}".format(node.lineno))
        if isinstance(node, ast.Attribute) and node.attr == "mcp_safe_session":
            bad_names.append("Attribute reference at line {}".format(node.lineno))

    assert not bad_imports, (
        "`_executor.py` must not import safe-session symbols — the module "
        "was removed 2026-05-16. Offenders:\n  " + "\n  ".join(bad_imports)
    )
    assert not bad_names, (
        "`_executor.py` must not call `mcp_safe_session(...)` — wrap-free "
        "dispatch is the post-2026-05-16 contract. Offenders:\n  " + "\n  ".join(bad_names)
    )


def test_public_init_does_not_export_safe_session_symbols() -> None:
    """``dcc_mcp_maya.__all__`` must not list ``mcp_safe_session`` / friends.

    The previous public surface re-exported ``mcp_safe_session`` /
    ``suppressed_dialog_calls`` / ``ENV_SAFE_SESSION``. All three are
    gone; this test fails if a refactor accidentally re-exports any
    of them (which would mean the symbol must still resolve, i.e.
    the module came back).
    """
    import dcc_mcp_maya

    public = getattr(dcc_mcp_maya, "__all__", ())
    for forbidden in ("mcp_safe_session", "suppressed_dialog_calls", "ENV_SAFE_SESSION"):
        assert forbidden not in public, (
            f"{forbidden!r} must not appear in dcc_mcp_maya.__all__ — the safe-session module was removed 2026-05-16."
        )
