"""Unit tests for tools/lint_skills.py."""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import List, Optional

# Make tools/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import lint_skills  # noqa: E402
import yaml  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_skill_dir(tmp_path: Path, skill_name: str, skill_md: str, scripts: Optional[List[str]] = None) -> Path:
    """Create a minimal skill directory for testing."""
    skill_dir = tmp_path / skill_name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    if scripts:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        for script in scripts:
            (scripts_dir / script).write_text("# placeholder", encoding="utf-8")
    return skill_dir


CLEAN_FRONTMATTER = dedent("""\
    ---
    name: maya-test
    description: "Test skill for unit tests"
    dcc: maya
    version: "1.0.0"
    tags: [maya, test]
    license: "MIT"
    depends: []
    ---

    # maya-test

    Test description.
""")


# ---------------------------------------------------------------------------
# check_conflict_markers
# ---------------------------------------------------------------------------


class TestCheckConflictMarkers:
    def test_no_conflict(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_conflict_markers(skill_dir, "maya-test", CLEAN_FRONTMATTER)
        assert issues == []

    def test_with_conflict(self, tmp_path):
        conflict_content = dedent("""\
            ---
            name: maya-test
            <<<<<<< HEAD
            description: "old"
            =======
            description: "new"
            >>>>>>> origin/main
            dcc: maya
            ---
        """)
        skill_dir = make_skill_dir(tmp_path, "maya-test", conflict_content)
        issues = lint_skills.check_conflict_markers(skill_dir, "maya-test", conflict_content)
        assert len(issues) == 1
        assert issues[0].rule == "CONFLICT_MARKER"
        assert issues[0].severity == "ERROR"

    def test_fix_removes_conflict(self, tmp_path):
        conflict_content = dedent("""\
            ---
            name: maya-test
            <<<<<<< HEAD
            description: "old"
            =======
            description: "new"
            >>>>>>> origin/main
            ---
        """)
        skill_dir = make_skill_dir(tmp_path, "maya-test", conflict_content)
        n = lint_skills.fix_conflict_markers(skill_dir)
        assert n == 1
        resolved = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "<<<<<<" not in resolved
        assert 'description: "new"' in resolved

    def test_fix_returns_zero_if_clean(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        n = lint_skills.fix_conflict_markers(skill_dir)
        assert n == 0


# ---------------------------------------------------------------------------
# check_frontmatter_parseable
# ---------------------------------------------------------------------------


class TestCheckFrontmatterParseable:
    def test_valid_frontmatter(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues, fm = lint_skills.check_frontmatter_parseable(skill_dir, "maya-test", CLEAN_FRONTMATTER)
        assert issues == []
        assert fm is not None
        assert fm["name"] == "maya-test"

    def test_missing_opening_dashes(self, tmp_path):
        content = "name: maya-test\ndcc: maya\n"
        skill_dir = make_skill_dir(tmp_path, "maya-test", content)
        issues, fm = lint_skills.check_frontmatter_parseable(skill_dir, "maya-test", content)
        assert any(i.rule == "NO_FRONTMATTER" for i in issues)
        assert fm is None

    def test_missing_closing_dashes(self, tmp_path):
        content = "---\nname: maya-test\ndcc: maya\n"
        skill_dir = make_skill_dir(tmp_path, "maya-test", content)
        issues, fm = lint_skills.check_frontmatter_parseable(skill_dir, "maya-test", content)
        assert any(i.rule == "NO_FRONTMATTER" for i in issues)
        assert fm is None


# ---------------------------------------------------------------------------
# check_name_field
# ---------------------------------------------------------------------------


class TestCheckNameField:
    def _make_fm(self, name):
        return {"name": name, "dcc": "maya"}

    def test_valid_name(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, "maya-test", self._make_fm("maya-test"))
        assert issues == []

    def test_missing_name(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, "maya-test", {})
        assert any(i.rule == "NO_NAME" and i.severity == "ERROR" for i in issues)

    def test_name_mismatch(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, "maya-test", self._make_fm("maya-other"))
        assert any(i.rule == "NAME_MISMATCH" and i.severity == "ERROR" for i in issues)

    def test_name_too_long(self, tmp_path):
        long_name = "maya-" + "a" * 60
        skill_dir = make_skill_dir(tmp_path, long_name, CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, long_name, self._make_fm(long_name))
        assert any(i.rule == "NAME_FORMAT" for i in issues)

    def test_name_starts_with_hyphen(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, "-maya-test", self._make_fm("-maya-test"))
        assert any(i.rule == "NAME_FORMAT" for i in issues)

    def test_name_ends_with_hyphen(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, "maya-test-", self._make_fm("maya-test-"))
        assert any(i.rule == "NAME_FORMAT" for i in issues)

    def test_name_consecutive_hyphens(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, "maya--test", self._make_fm("maya--test"))
        assert any(i.rule == "NAME_FORMAT" for i in issues)

    def test_name_invalid_chars(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_name_field(skill_dir, "Maya_Test", self._make_fm("Maya_Test"))
        assert any(i.rule == "NAME_FORMAT" for i in issues)


# ---------------------------------------------------------------------------
# check_dcc_field
# ---------------------------------------------------------------------------


class TestCheckDccField:
    def test_valid_maya_dcc(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_dcc_field(skill_dir, "maya-test", {"dcc": "maya"})
        assert issues == []

    def test_wrong_dcc_for_project(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_dcc_field(skill_dir, "maya-test", {"dcc": "blender"})
        assert any(i.rule == "WRONG_DCC" and i.severity == "ERROR" for i in issues)

    def test_unknown_dcc(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_dcc_field(skill_dir, "maya-test", {"dcc": "unknown_app"})
        assert any(i.rule == "UNKNOWN_DCC" for i in issues)
        assert any(i.rule == "WRONG_DCC" for i in issues)

    def test_default_python_dcc(self, tmp_path):
        """dcc defaults to 'python' if not set — should trigger WRONG_DCC for this project."""
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_dcc_field(skill_dir, "maya-test", {})
        assert any(i.rule == "WRONG_DCC" for i in issues)


# ---------------------------------------------------------------------------
# check_version_field
# ---------------------------------------------------------------------------


class TestCheckVersionField:
    def test_valid_version(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        for ver in ["1.0.0", "2.3.4", "0.1"]:
            issues = lint_skills.check_version_field(skill_dir, "maya-test", {"version": ver})
            assert issues == [], f"Expected no issues for version '{ver}'"

    def test_invalid_version(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        for ver in ["v1.0.0", "1.0.0.0", "latest", "abc"]:
            issues = lint_skills.check_version_field(skill_dir, "maya-test", {"version": ver})
            assert any(i.rule == "BAD_VERSION" for i in issues), f"Expected BAD_VERSION for '{ver}'"


# ---------------------------------------------------------------------------
# check_description_field
# ---------------------------------------------------------------------------


class TestCheckDescriptionField:
    def test_valid_description(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_description_field(skill_dir, "maya-test", {"description": "A skill"})
        assert issues == []

    def test_missing_description(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_description_field(skill_dir, "maya-test", {})
        assert any(i.rule == "MISSING_DESC" for i in issues)

    def test_empty_description(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_description_field(skill_dir, "maya-test", {"description": ""})
        assert any(i.rule == "MISSING_DESC" for i in issues)

    def test_description_too_long(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        long_desc = "A" * 1025
        issues = lint_skills.check_description_field(skill_dir, "maya-test", {"description": long_desc})
        assert any(i.rule == "DESC_TOO_LONG" for i in issues)


# ---------------------------------------------------------------------------
# check_scripts_section
# ---------------------------------------------------------------------------


class TestCheckScriptsSection:
    def test_no_scripts_dir(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_scripts_section(skill_dir, "maya-test", CLEAN_FRONTMATTER)
        assert issues == []

    def test_scripts_with_section(self, tmp_path):
        content = CLEAN_FRONTMATTER + "\n## Scripts\n\n- `my_script` — does stuff\n"
        skill_dir = make_skill_dir(tmp_path, "maya-test", content, scripts=["my_script.py"])
        issues = lint_skills.check_scripts_section(skill_dir, "maya-test", content)
        assert issues == []

    def test_scripts_without_section(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER, scripts=["my_script.py"])
        issues = lint_skills.check_scripts_section(skill_dir, "maya-test", CLEAN_FRONTMATTER)
        assert any(i.rule == "MISSING_SCRIPTS_SECTION" for i in issues)


# ---------------------------------------------------------------------------
# check_tools_source_files
# ---------------------------------------------------------------------------


class TestCheckToolsSourceFiles:
    def test_no_tools(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_tools_source_files(skill_dir, "maya-test", {})
        assert issues == []

    def test_tools_source_exists(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER, scripts=["do_thing.py"])
        fm = {"tools": [{"name": "do_thing", "source_file": "scripts/do_thing.py"}]}
        issues = lint_skills.check_tools_source_files(skill_dir, "maya-test", fm)
        assert issues == []

    def test_tools_source_missing(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        fm = {"tools": [{"name": "do_thing", "source_file": "scripts/do_thing.py"}]}
        issues = lint_skills.check_tools_source_files(skill_dir, "maya-test", fm)
        assert any(i.rule == "TOOL_SOURCE_MISSING" for i in issues)


# ---------------------------------------------------------------------------
# check_depends_exist
# ---------------------------------------------------------------------------


class TestCheckDependsExist:
    def test_no_depends(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        issues = lint_skills.check_depends_exist(skill_dir, "maya-test", {}, {"maya-other"})
        assert issues == []

    def test_depends_exists(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        fm = {"depends": ["maya-scene"]}
        issues = lint_skills.check_depends_exist(skill_dir, "maya-test", fm, {"maya-scene", "maya-test"})
        assert issues == []

    def test_depends_missing(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        fm = {"depends": ["maya-nonexistent"]}
        issues = lint_skills.check_depends_exist(skill_dir, "maya-test", fm, {"maya-scene"})
        assert any(i.rule == "MISSING_DEPENDS" for i in issues)


class TestCheckDccMcpMetadataKeys:
    def test_known_nested_keys(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        fm = {"metadata": {"dcc-mcp": {"dcc": "maya", "tools": "tools.yaml", "recipes": "references/RECIPES.md"}}}
        issues = lint_skills.check_dcc_mcp_metadata_keys(skill_dir, "maya-test", fm)
        assert issues == []

    def test_unknown_nested_key_warns(self, tmp_path):
        skill_dir = make_skill_dir(tmp_path, "maya-test", CLEAN_FRONTMATTER)
        fm = {"metadata": {"dcc-mcp": {"aliases": ["maya-old-name"]}}}
        issues = lint_skills.check_dcc_mcp_metadata_keys(skill_dir, "maya-test", fm)
        assert any(i.rule == "UNKNOWN_DCC_MCP_METADATA" for i in issues)


# ---------------------------------------------------------------------------
# check_duplicate_action_names (cross-skill)
# ---------------------------------------------------------------------------


class TestCheckDuplicateActionNames:
    def test_no_duplicates(self, tmp_path):
        info_a = lint_skills.SkillInfo(
            name="skill-a",
            skill_dir=tmp_path / "skill-a",
            scripts=[tmp_path / "skill-a" / "scripts" / "alpha.py"],
            tools=[("alpha", tmp_path / "skill-a" / "tools.yaml", {"name": "alpha"})],
        )
        info_b = lint_skills.SkillInfo(
            name="skill-b",
            skill_dir=tmp_path / "skill-b",
            scripts=[tmp_path / "skill-b" / "scripts" / "beta.py"],
            tools=[("beta", tmp_path / "skill-b" / "tools.yaml", {"name": "beta"})],
        )
        issues = lint_skills.check_duplicate_action_names([info_a, info_b])
        assert issues == []

    def test_with_duplicates(self, tmp_path):
        info_a = lint_skills.SkillInfo(
            name="skill-a",
            skill_dir=tmp_path / "skill-a",
            scripts=[tmp_path / "skill-a" / "scripts" / "shared.py"],
            tools=[("shared", tmp_path / "skill-a" / "tools.yaml", {"name": "shared"})],
        )
        info_b = lint_skills.SkillInfo(
            name="skill-b",
            skill_dir=tmp_path / "skill-b",
            scripts=[tmp_path / "skill-b" / "scripts" / "shared.py"],
            tools=[("shared", tmp_path / "skill-b" / "tools.yaml", {"name": "shared"})],
        )
        issues = lint_skills.check_duplicate_action_names([info_a, info_b])
        assert len(issues) == 2  # one per skill
        assert all(i.rule == "DUPLICATE_SCRIPT_STEM" for i in issues)
        assert all(i.severity == "WARNING" for i in issues)

    def test_duplicate_manifest_actions_are_errors(self, tmp_path):
        info_a = lint_skills.SkillInfo(
            name="skill-a",
            skill_dir=tmp_path / "skill-a",
            tools=[("shared", tmp_path / "skill-a" / "tools.yaml", {"name": "shared"})],
        )
        info_b = lint_skills.SkillInfo(
            name="skill-b",
            skill_dir=tmp_path / "skill-b",
            tools=[("shared", tmp_path / "skill-b" / "tools.yaml", {"name": "shared"})],
        )
        issues = lint_skills.check_duplicate_tool_action_names([info_a, info_b])
        assert len(issues) == 2
        assert all(i.rule == "DUPLICATE_TOOL_ACTION" for i in issues)
        assert all(i.severity == "ERROR" for i in issues)

    def test_deprecated_alias_exempts_duplicate_manifest_action(self, tmp_path):
        info_a = lint_skills.SkillInfo(
            name="skill-a",
            skill_dir=tmp_path / "skill-a",
            tools=[("shared", tmp_path / "skill-a" / "tools.yaml", {"name": "shared"})],
        )
        info_b = lint_skills.SkillInfo(
            name="skill-b",
            skill_dir=tmp_path / "skill-b",
            tools=[
                (
                    "shared",
                    tmp_path / "skill-b" / "tools.yaml",
                    {"name": "shared", "deprecated_alias_for": "skill-a.shared"},
                )
            ],
        )
        issues = lint_skills.check_duplicate_tool_action_names([info_a, info_b])
        assert issues == []


# ---------------------------------------------------------------------------
# Bundled tools.yaml contract
# ---------------------------------------------------------------------------


class TestBundledToolsYamlContract:
    def _bundled_tools(self):
        skills_root = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills"
        for tools_yaml in sorted(skills_root.glob("*/tools.yaml")):
            data = yaml.safe_load(tools_yaml.read_text(encoding="utf-8")) or {}
            for tool in data.get("tools", []):
                yield tools_yaml.parent.name, tools_yaml, tool

    def test_every_exposed_tool_has_agent_facing_description(self):
        missing = [
            "{}:{}".format(skill, tool.get("name"))
            for skill, _path, tool in self._bundled_tools()
            if not str(tool.get("description", "")).strip()
        ]
        assert missing == []

    def test_create_sphere_has_single_canonical_exposed_tool(self):
        owners = [skill for skill, _path, tool in self._bundled_tools() if tool.get("name") == "create_sphere"]
        assert owners == ["maya-primitives"]

    def test_affinity_declarations_use_core_default_enforcement(self):
        redundant_enforcement = []
        duplicate_aliases = []
        for skill, _path, tool in self._bundled_tools():
            affinity = tool.get("affinity")
            if affinity not in {"main", "any"}:
                continue
            label = "{}:{}".format(skill, tool.get("name"))
            if "enforce_thread_affinity" in tool:
                redundant_enforcement.append(label)
            if "thread_affinity" in tool:
                duplicate_aliases.append(label)

        assert redundant_enforcement == []
        assert duplicate_aliases == []


# ---------------------------------------------------------------------------
# lint_all integration
# ---------------------------------------------------------------------------


class TestLintAll:
    def test_clean_skill_passes(self, tmp_path):
        make_skill_dir(tmp_path, "maya-clean", CLEAN_FRONTMATTER.replace("maya-test", "maya-clean"))
        issues = lint_skills.lint_all(tmp_path)
        errors = [i for i in issues if i.severity == "ERROR"]
        assert errors == []

    def test_conflict_marker_is_error(self, tmp_path):
        conflict_md = dedent("""\
            ---
            name: maya-bad
            <<<<<<< HEAD
            description: "old"
            =======
            description: "new"
            >>>>>>> origin/main
            dcc: maya
            ---
        """)
        make_skill_dir(tmp_path, "maya-bad", conflict_md)
        issues = lint_skills.lint_all(tmp_path)
        assert any(i.rule == "CONFLICT_MARKER" and i.severity == "ERROR" for i in issues)

    def test_fix_resolves_conflicts(self, tmp_path):
        conflict_md = dedent("""\
            ---
            name: maya-bad
            <<<<<<< HEAD
            description: "old"
            =======
            description: "new"
            >>>>>>> origin/main
            dcc: maya
            version: "1.0.0"
            ---
        """)
        make_skill_dir(tmp_path, "maya-bad", conflict_md)
        issues = lint_skills.lint_all(tmp_path, fix=True)
        conflict_issues = [i for i in issues if i.rule == "CONFLICT_MARKER"]
        assert conflict_issues == []

    def test_error_only_filter(self, tmp_path):
        # Skill with a warning only (missing scripts section)
        content = CLEAN_FRONTMATTER.replace("maya-test", "maya-ok")
        make_skill_dir(tmp_path, "maya-ok", content, scripts=["do_thing.py"])
        issues = lint_skills.lint_all(tmp_path, error_only=True)
        warnings = [i for i in issues if i.severity == "WARNING"]
        assert warnings == []
