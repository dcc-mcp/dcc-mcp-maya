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

import os
import re
import sys
import types
from pathlib import Path
from typing import Dict, Iterator, List

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
# Safe-session firewall
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_maya_cmds() -> Iterator[types.SimpleNamespace]:
    """Inject a tiny fake ``maya.cmds`` so ``mcp_safe_session`` engages.

    The fake records every call to ``autoSave`` and to each modal
    dialog so we can assert the safe-session wrapper:

    * disables AutoSave for the block,
    * patches the dialog functions to non-blocking stubs,
    * restores everything on exit.
    """
    autosave_state: Dict[str, bool] = {"enabled": True}
    autosave_calls: List[Dict[str, object]] = []

    def auto_save(query: bool = False, enable: bool = False) -> bool:
        autosave_calls.append({"query": query, "enable": enable})
        if query:
            return autosave_state["enabled"]
        autosave_state["enabled"] = bool(enable)
        return autosave_state["enabled"]

    def confirm_dialog(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("real confirmDialog must NEVER fire under mcp_safe_session")

    def file_dialog2(*_args: object, **_kwargs: object) -> List[str]:
        raise AssertionError("real fileDialog2 must NEVER fire under mcp_safe_session")

    cmds = types.SimpleNamespace(
        autoSave=auto_save,
        confirmDialog=confirm_dialog,
        promptDialog=confirm_dialog,
        fileDialog=file_dialog2,
        fileDialog2=file_dialog2,
        layoutDialog=confirm_dialog,
        # Auxiliary state for assertions.
        _autosave_calls=autosave_calls,
        _autosave_state=autosave_state,
    )
    fake_maya = types.ModuleType("maya")
    fake_maya.cmds = cmds  # type: ignore[attr-defined]
    sys.modules["maya"] = fake_maya
    sys.modules["maya.cmds"] = cmds  # type: ignore[assignment]
    try:
        yield cmds
    finally:
        sys.modules.pop("maya.cmds", None)
        sys.modules.pop("maya", None)


def test_safe_session_is_noop_without_maya() -> None:
    """Without ``maya.cmds`` importable, the context is a transparent no-op."""
    from dcc_mcp_maya._safe_session import mcp_safe_session, suppressed_dialog_calls

    with mcp_safe_session():
        assert suppressed_dialog_calls() == []


def test_safe_session_is_noop_when_env_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    from dcc_mcp_maya._safe_session import (
        ENV_SAFE_SESSION,
        mcp_safe_session,
        suppressed_dialog_calls,
    )

    monkeypatch.setenv(ENV_SAFE_SESSION, "0")
    with mcp_safe_session():
        # Even with the env opt-out, calling the helper must not crash.
        assert suppressed_dialog_calls() == []


def test_safe_session_disables_autosave_and_restores(fake_maya_cmds: types.SimpleNamespace) -> None:
    from dcc_mcp_maya._safe_session import mcp_safe_session

    assert fake_maya_cmds._autosave_state["enabled"] is True
    with mcp_safe_session():
        # AutoSave is paused for the block.
        assert fake_maya_cmds._autosave_state["enabled"] is False
    # And restored on exit.
    assert fake_maya_cmds._autosave_state["enabled"] is True


def test_safe_session_intercepts_dialogs_and_records(fake_maya_cmds: types.SimpleNamespace) -> None:
    from dcc_mcp_maya._safe_session import mcp_safe_session, suppressed_dialog_calls

    with mcp_safe_session():
        # These would deadlock the dispatcher in real Maya.
        result = fake_maya_cmds.confirmDialog(title="Save?", message="Hello")
        assert result == "dismiss"
        files = fake_maya_cmds.fileDialog2(title="Pick a file")
        assert files == []
        # The recorder captured both calls (titles included for audit).
        captured = suppressed_dialog_calls()
        assert any("confirmDialog" in c for c in captured), captured
        assert any("fileDialog2" in c for c in captured), captured

    # After exit the originals are restored — the next call would raise
    # AssertionError from the fake fixture, proving the patch was undone.
    with pytest.raises(AssertionError):
        fake_maya_cmds.confirmDialog(title="real")


def test_safe_session_is_reentrant(fake_maya_cmds: types.SimpleNamespace) -> None:
    """Nested invocations refcount; only the outermost exit restores state."""
    from dcc_mcp_maya._safe_session import mcp_safe_session

    with mcp_safe_session():
        outer_disabled = fake_maya_cmds._autosave_state["enabled"]
        with mcp_safe_session():
            # AutoSave already paused; nested entry must not flip it back.
            assert fake_maya_cmds._autosave_state["enabled"] is False
            # Dialog patches still active.
            assert fake_maya_cmds.confirmDialog(title="nested") == "dismiss"
        # After inner exit, still inside outer scope → state stays patched.
        assert fake_maya_cmds._autosave_state["enabled"] is False
        assert outer_disabled is False
    # Only after the outer exit does AutoSave come back.
    assert fake_maya_cmds._autosave_state["enabled"] is True


def test_safe_session_restores_on_exception(fake_maya_cmds: types.SimpleNamespace) -> None:
    from dcc_mcp_maya._safe_session import mcp_safe_session

    class _Boom(RuntimeError):
        pass

    with pytest.raises(_Boom):
        with mcp_safe_session():
            assert fake_maya_cmds._autosave_state["enabled"] is False
            raise _Boom("simulated skill failure")
    # AutoSave + dialog patches restored even though the body raised.
    assert fake_maya_cmds._autosave_state["enabled"] is True
    with pytest.raises(AssertionError):
        fake_maya_cmds.confirmDialog(title="post-exception")


# ---------------------------------------------------------------------------
# Cleanup so the env var fixture above does not leak into other tests.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_safe_session_env() -> Iterator[None]:
    saved = os.environ.get("DCC_MCP_MAYA_SAFE_SESSION")
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop("DCC_MCP_MAYA_SAFE_SESSION", None)
        else:
            os.environ["DCC_MCP_MAYA_SAFE_SESSION"] = saved
