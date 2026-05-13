"""Maya minimal-mode configuration + dynamic stage taxonomy helpers.

The real progressive-loading machinery lives in ``dcc-mcp-core``.
This module only owns:

1. The Maya-side default for *which* skills are loaded eagerly when
   minimal mode is on (:data:`MINIMAL_SKILLS`).
2. Maya's preferred **stage vocabulary** (:data:`STAGES`) so tooling
   that surfaces stage labels has a deterministic display order.
3. Thin helpers that read each skill's stage at runtime from its
   ``SKILL.md`` frontmatter via :func:`dcc_mcp_core.parse_skill_md`,
   and that derive minimal-mode group deactivation from each skill's
   ``groups.yaml`` (``default_active: false`` → deactivate).

Both the ``{skill_name → stage}`` and ``{skill_name → deactivate_groups}``
maps used to live here as hand-maintained dictionaries.  That violated
the single-source-of-truth rule — every ``SKILL.md`` already declares
``metadata.dcc-mcp.stage`` and every ``groups.yaml`` already declares
``default_active`` per group.  The hard-coded mirrors also silently
ignored user-installed and team-level skills.  This module now derives
everything from disk on demand so adding a new bundled skill (or a user
skill that opts into the same vocabulary) needs no Python edits.
"""

from __future__ import annotations

# Import built-in modules
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Tuple

# Import third-party modules
import dcc_mcp_core as _dcc_mcp_core
from dcc_mcp_core import MinimalModeConfig

_core_parse_skill_md = _dcc_mcp_core.parse_skill_md


def _extract_stage_from_skill_md(skill_dir: Path) -> Optional[str]:
    """Read ``metadata.dcc-mcp.stage`` from SKILL.md without PyYAML."""
    skill_md = skill_dir / "SKILL.md"
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    in_frontmatter = False
    in_metadata = False
    in_dcc_mcp = False
    metadata_indent = 0
    dcc_mcp_indent = 0
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if not in_frontmatter or not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if stripped == "metadata:":
            in_metadata = True
            metadata_indent = indent
            in_dcc_mcp = False
            continue
        if in_metadata and indent <= metadata_indent and not stripped.startswith("metadata:"):
            in_metadata = False
            in_dcc_mcp = False
        if in_metadata and stripped == "dcc-mcp:":
            in_dcc_mcp = True
            dcc_mcp_indent = indent
            continue
        if in_dcc_mcp and indent <= dcc_mcp_indent and not stripped.startswith("dcc-mcp:"):
            in_dcc_mcp = False
        if in_dcc_mcp and stripped.startswith("stage:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return value or None
    return None


def parse_skill_md(skill_dir: str):
    """Compatibility wrapper for core wheels that ignore dcc-mcp stage."""
    meta = _core_parse_skill_md(skill_dir)
    if meta is None or getattr(meta, "stage", None):
        return meta
    stage = _extract_stage_from_skill_md(Path(skill_dir))
    if stage:
        try:
            setattr(meta, "stage", stage)
        except Exception:

            class _SkillMetadataStageProxy:
                def __init__(self, wrapped, parsed_stage: str) -> None:
                    self._wrapped = wrapped
                    self.stage = parsed_stage

                def __getattr__(self, name: str):
                    return getattr(self._wrapped, name)

            return _SkillMetadataStageProxy(meta, stage)
    return meta


_dcc_mcp_core.parse_skill_md = parse_skill_md

#: Skills loaded eagerly when minimal mode is on.  ``maya-scripting``
#: is the bootstrap fall-through; ``maya-scene`` provides the
#: read-only scene queries every agent needs to orient itself.
MINIMAL_SKILLS: Tuple[str, ...] = ("maya-scripting", "maya-scene")

#: Maya's canonical pipeline-stage vocabulary, in display / activation
#: order.  Each value is the string a bundled ``SKILL.md`` writes under
#: ``metadata.dcc-mcp.stage``.  The vocabulary is owned by Maya — other
#: DCC adapters may use a different one (Houdini might add
#: ``simulation``, Photoshop might add ``compositing``).  ``dcc-mcp-core``
#: deliberately does not validate the value, so adapters can evolve their
#: stage taxonomy without an upstream release.
STAGES: Tuple[str, ...] = (
    "bootstrap",
    "scene",
    "authoring",
    "interchange",
    "pipeline",
)

#: Path to the bundled-skills directory shipped inside this package.
_BUNDLED_SKILLS_DIR: Path = Path(__file__).resolve().parent / "skills"


# ── Dynamic stage discovery ──────────────────────────────────────────


def _read_stage(skill_dir: Path) -> Optional[str]:
    """Return the stage declared by *skill_dir*'s ``SKILL.md`` (or None).

    Uses :func:`dcc_mcp_core.parse_skill_md`, which is the same parser
    the live catalog uses; the value comes straight off
    ``metadata.dcc-mcp.stage`` in the YAML frontmatter.  We do not cache
    individual reads because the directory walk in
    :func:`_iter_bundled_stages` is already cached as a whole.
    """

    if not (skill_dir / "SKILL.md").is_file():
        return None
    meta = parse_skill_md(str(skill_dir))
    if meta is None:
        return None
    stage = getattr(meta, "stage", None)
    if isinstance(stage, str) and stage:
        return stage
    return None


@lru_cache(maxsize=1)
def _bundled_stage_map() -> Dict[str, str]:
    """Walk the bundled-skills directory and return ``{skill_name → stage}``.

    Skills whose ``SKILL.md`` does not declare a stage are silently
    omitted — :func:`skills_for_stage` then will not return them, and
    they remain accessible via the explicit ``load_skill`` path.

    Cached with :func:`functools.lru_cache` because the bundled
    directory is read-only at runtime; tests that need a fresh read
    after writing fixtures should call :func:`_clear_bundled_cache`.
    """

    mapping: Dict[str, str] = {}
    if not _BUNDLED_SKILLS_DIR.is_dir():
        return mapping
    for entry in sorted(_BUNDLED_SKILLS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        stage = _read_stage(entry)
        if stage is not None:
            mapping[entry.name] = stage
    return mapping


def _read_default_inactive_groups(skill_dir: Path) -> Tuple[str, ...]:
    """Return the names of every group declared with ``default_active: false``
    in ``<skill_dir>/groups.yaml``.

    The bundled skills' ``groups.yaml`` files are tiny YAML mappings of
    the shape::

        groups:
          - name: core
            default_active: true
            tools: [...]
          - name: introspect
            default_active: false
            tools: [...]

    We avoid pulling in PyYAML (this module needs to import in
    minimal-venv contexts such as `mayapy` smoke checks).  The parser
    is intentionally narrow: it tolerates only the canonical shape
    that every bundled skill in this repo uses.  Anything more exotic
    falls back to "no default-inactive groups" — better to surface
    nothing than to silently misclassify.
    """

    groups_path = skill_dir / "groups.yaml"
    if not groups_path.is_file():
        return ()

    try:
        raw_lines = groups_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()

    inactive: list[str] = []
    current_name: Optional[str] = None
    current_default_active: Optional[bool] = None

    def _flush() -> None:
        if current_name and current_default_active is False:
            inactive.append(current_name)

    for line in raw_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # New group entry — flush the previous one.
        if stripped.startswith("- name:") or stripped.startswith("-name:"):
            _flush()
            current_name = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            current_default_active = None
            continue
        if stripped.startswith("name:") and line.startswith(("  ", "\t")):
            # Continuation `name:` (rare formatting); treat as new group.
            _flush()
            current_name = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            current_default_active = None
            continue
        if stripped.startswith("default_active:") or stripped.startswith("default-active:"):
            value = stripped.split(":", 1)[1].strip().lower()
            if value in ("false", "no", "off", "0"):
                current_default_active = False
            elif value in ("true", "yes", "on", "1"):
                current_default_active = True
    _flush()
    return tuple(inactive)


@lru_cache(maxsize=1)
def _bundled_default_inactive_groups() -> Dict[str, Tuple[str, ...]]:
    """Return ``{skill_name → tuple_of_default_inactive_group_names}`` for
    every bundled skill that ships a ``groups.yaml``.

    This replaces the pre-0.2.x ``MINIMAL_DEACTIVATE_GROUPS`` constant.
    The data is the projection of each ``groups.yaml`` onto the names
    whose ``default_active`` is ``false`` — exactly the groups
    minimal-mode should leave inactive after :func:`load_skill` runs.
    Skills with no ``groups.yaml``, or with every group default-active,
    contribute no entry.
    """

    mapping: Dict[str, Tuple[str, ...]] = {}
    if not _BUNDLED_SKILLS_DIR.is_dir():
        return mapping
    for entry in sorted(_BUNDLED_SKILLS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        inactive = _read_default_inactive_groups(entry)
        if inactive:
            mapping[entry.name] = inactive
    return mapping


def _default_minimal_deactivate_groups(
    skills: Iterable[str],
) -> Dict[str, Tuple[str, ...]]:
    """Project :func:`_bundled_default_inactive_groups` onto the supplied
    *skills* set.

    Returns a fresh ``dict`` (suitable for ``MinimalModeConfig`` which
    accepts ``Mapping[str, tuple[str, ...]]``).  Skills the caller did
    not request are dropped — minimal mode only needs deactivation
    instructions for skills it actually loads.
    """

    full = _bundled_default_inactive_groups()
    requested = set(skills)
    return {name: groups for name, groups in full.items() if name in requested}


def _clear_bundled_cache() -> None:
    """Drop every cached bundled-skill view (for tests / hot reload)."""

    _bundled_stage_map.cache_clear()
    _bundled_default_inactive_groups.cache_clear()


def _iter_bundled_stages() -> Iterator[Tuple[str, str]]:
    """Iterate ``(skill_name, stage)`` for every bundled skill that
    declares a stage.  Order is filesystem-sorted for determinism."""

    return iter(_bundled_stage_map().items())


def skills_for_stage(stage: str) -> Tuple[str, ...]:
    """Return every bundled skill whose ``SKILL.md`` declares *stage*.

    The set is derived dynamically from each ``SKILL.md`` frontmatter —
    no hard-coded mapping exists in this module.  A skill is considered
    "bundled" if it lives under ``src/dcc_mcp_maya/skills/<name>/``.

    Args:
        stage: One of :data:`STAGES`.

    Returns:
        Tuple of skill names in alphabetical order (deterministic).

    Raises:
        ValueError: When *stage* is not a recognised pipeline stage.
    """

    if stage not in STAGES:
        raise ValueError(
            "Unknown stage {!r}; expected one of {}".format(stage, STAGES),
        )
    return tuple(name for name, st in _iter_bundled_stages() if st == stage)


def build_minimal_mode_config(skill_names: Optional[Iterable[str]] = None) -> MinimalModeConfig:
    """Build Maya's declarative minimal-mode config for core.

    Args:
        skill_names: Override the default :data:`MINIMAL_SKILLS` set.
            Pass ``None`` to use the canonical default (bootstrap +
            scene/core only).

    Returns:
        :class:`dcc_mcp_core.MinimalModeConfig` ready to forward to
        ``DccServerBase.register_builtin_actions(minimal_mode=...)``.
        ``deactivate_groups`` is derived dynamically from each loaded
        skill's ``groups.yaml`` (``default_active: false`` → deactivate)
        — no Python edit needed when a skill author flips a group's
        default state.
    """

    skills = tuple(skill_names) if skill_names is not None else MINIMAL_SKILLS
    return MinimalModeConfig(
        skills=skills,
        deactivate_groups=_default_minimal_deactivate_groups(skills),
    )


def build_minimal_mode_for_stages(stages: Iterable[str]) -> MinimalModeConfig:
    """Build a minimal-mode config that eagerly loads whole *stages*.

    Useful when an operator wants, say, *bootstrap + scene + interchange*
    pre-loaded so an FBX round-trip works without an explicit
    ``load_skill`` call from the agent::

        cfg = build_minimal_mode_for_stages(["bootstrap", "scene", "interchange"])
        server.register_builtin_actions(minimal_mode=cfg)

    Bootstrap is always included so ``execute_python`` stays reachable.

    Stage membership is derived dynamically from each bundled
    ``SKILL.md`` frontmatter via :func:`skills_for_stage`, so adding
    a new skill in any of the requested stages picks it up
    automatically — no Python edit required.

    Args:
        stages: Stage names from :data:`STAGES`.  Order is irrelevant;
            the returned skill list is sorted by stage then by skill
            name for determinism.

    Returns:
        :class:`MinimalModeConfig` whose ``skills`` covers every skill
        in the requested stages and whose ``deactivate_groups``
        respects the standard minimal-mode group policy for the
        always-on stages.

    Raises:
        ValueError: When an unknown stage is supplied.
    """

    requested = set(stages)
    requested.add("bootstrap")  # never lose the fall-through
    unknown = requested - set(STAGES)
    if unknown:
        raise ValueError(
            "Unknown stage(s): {}; expected subset of {}".format(sorted(unknown), STAGES),
        )

    eager: list[str] = []
    for stage in STAGES:
        if stage in requested:
            eager.extend(sorted(skills_for_stage(stage)))
    return MinimalModeConfig(
        skills=tuple(eager),
        deactivate_groups=_default_minimal_deactivate_groups(eager),
    )
