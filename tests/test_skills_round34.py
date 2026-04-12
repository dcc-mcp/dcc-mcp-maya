"""Round 34 — maya_warning helper + SKILL.md tools: field validation.

Covers:
- maya_warning(): success=True with context["warning"] key
- maya_warning imported from dcc_mcp_maya top-level package
- maya_warning in api.__all__
- SKILL.md tools: field structure (ToolDeclaration-compatible)
- 4 updated SKILL.md files contain valid tools: arrays
"""

# Import built-in modules
import os

# Import third-party modules
import pytest

# ---------------------------------------------------------------------------
# TestMayaWarning
# ---------------------------------------------------------------------------


class TestMayaWarning:
    """Tests for the maya_warning() helper added in Round 34."""

    def test_returns_success_true(self):
        from dcc_mcp_maya.api import maya_warning

        result = maya_warning("Done with caveat", warning="fallback used")
        assert result["success"] is True

    def test_message_preserved(self):
        from dcc_mcp_maya.api import maya_warning

        result = maya_warning("Operation complete", warning="minor issue")
        assert result["message"] == "Operation complete"

    def test_warning_in_context(self):
        from dcc_mcp_maya.api import maya_warning

        result = maya_warning("Applied", warning="Arnold not available; used Lambert")
        assert "warning" in result["context"]
        assert "Arnold not available" in result["context"]["warning"]

    def test_empty_warning_allowed(self):
        from dcc_mcp_maya.api import maya_warning

        result = maya_warning("Done")
        assert result["success"] is True
        assert result["context"].get("warning", "") == ""

    def test_prompt_forwarded(self):
        from dcc_mcp_maya.api import maya_warning

        result = maya_warning(
            "Done",
            warning="check log",
            prompt="Review the output before proceeding.",
        )
        assert result.get("prompt") == "Review the output before proceeding."

    def test_extra_context_forwarded(self):
        from dcc_mcp_maya.api import maya_warning

        result = maya_warning(
            "Assigned",
            warning="fallback",
            object_name="pSphere1",
            material="lambert1",
        )
        assert result["context"]["object_name"] == "pSphere1"
        assert result["context"]["material"] == "lambert1"

    def test_no_error_key(self):
        from dcc_mcp_maya.api import maya_warning

        result = maya_warning("Done", warning="minor")
        # Should not have a non-None error field (it's a success variant)
        assert result.get("error") is None

    def test_importable_from_top_level(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "maya_warning")
        assert callable(dcc_mcp_maya.maya_warning)

    def test_top_level_returns_same_shape(self):
        import dcc_mcp_maya

        result = dcc_mcp_maya.maya_warning("Done", warning="test warning")
        assert result["success"] is True
        assert "warning" in result["context"]

    def test_in_api_all(self):
        from dcc_mcp_maya import api

        assert "maya_warning" in api.__all__

    def test_in_package_all(self):
        import dcc_mcp_maya

        assert "maya_warning" in dcc_mcp_maya.__all__


# ---------------------------------------------------------------------------
# TestSkillMdToolsField
# ---------------------------------------------------------------------------

SKILLS_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "dcc_mcp_maya",
    "skills",
)

SKILL_NAMES_WITH_TOOLS = [
    "maya-scene",
    "maya-primitives",
    "maya-animation",
    "maya-render",
]


class TestSkillMdToolsField:
    """Validate that the 4 updated SKILL.md files contain valid tools: arrays."""

    def _read_skill_md(self, skill_name):
        skill_md = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
        assert os.path.exists(skill_md), "SKILL.md not found: {}".format(skill_md)
        with open(skill_md, encoding="utf-8") as fh:
            return fh.read()

    def _parse_frontmatter(self, content):
        """Extract YAML frontmatter between --- delimiters."""
        # Import built-in modules
        import re

        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, "No YAML frontmatter found"
        # Import third-party modules
        import yaml

        return yaml.safe_load(match.group(1))

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_tools_key_present(self, skill_name):
        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        assert "tools" in fm, "tools: field missing in {}".format(skill_name)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_tools_is_list(self, skill_name):
        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        assert isinstance(fm["tools"], list), "tools: must be a list in {}".format(skill_name)
        assert len(fm["tools"]) > 0, "tools: list must not be empty in {}".format(skill_name)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_each_tool_has_required_fields(self, skill_name):
        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        for tool in fm["tools"]:
            assert "name" in tool, "tool missing 'name' in {}".format(skill_name)
            assert "description" in tool, "tool missing 'description' in {}".format(skill_name)
            assert "source_file" in tool, "tool missing 'source_file' in {}".format(skill_name)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_tool_annotations_present(self, skill_name):
        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        for tool in fm["tools"]:
            assert "read_only" in tool, "tool '{}' missing read_only in {}".format(tool.get("name", "?"), skill_name)
            assert "destructive" in tool, "tool '{}' missing destructive in {}".format(
                tool.get("name", "?"), skill_name
            )
            assert "idempotent" in tool, "tool '{}' missing idempotent in {}".format(tool.get("name", "?"), skill_name)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_source_file_under_scripts(self, skill_name):
        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        for tool in fm["tools"]:
            sf = tool.get("source_file", "")
            assert sf.startswith("scripts/"), "source_file '{}' must start with 'scripts/' in {}".format(sf, skill_name)

    def test_maya_scene_tool_count(self):
        content = self._read_skill_md("maya-scene")
        fm = self._parse_frontmatter(content)
        assert len(fm["tools"]) >= 8

    def test_maya_primitives_tool_count(self):
        content = self._read_skill_md("maya-primitives")
        fm = self._parse_frontmatter(content)
        assert len(fm["tools"]) == 8

    def test_maya_animation_tool_count(self):
        content = self._read_skill_md("maya-animation")
        fm = self._parse_frontmatter(content)
        assert len(fm["tools"]) >= 7

    def test_maya_render_tool_count(self):
        content = self._read_skill_md("maya-render")
        fm = self._parse_frontmatter(content)
        assert len(fm["tools"]) == 3

    def test_readonly_tools_not_destructive(self):
        """read_only=True tools should not be destructive."""
        for skill_name in SKILL_NAMES_WITH_TOOLS:
            content = self._read_skill_md(skill_name)
            fm = self._parse_frontmatter(content)
            for tool in fm["tools"]:
                if tool.get("read_only") is True:
                    assert tool.get("destructive") is False, (
                        "read_only tool '{}' in {} should not be destructive".format(tool.get("name"), skill_name)
                    )

    def test_tool_names_match_source_file_stems(self):
        """Each tool's name should match the stem of its source_file."""
        for skill_name in SKILL_NAMES_WITH_TOOLS:
            content = self._read_skill_md(skill_name)
            fm = self._parse_frontmatter(content)
            for tool in fm["tools"]:
                stem = os.path.splitext(os.path.basename(tool.get("source_file", "")))[0]
                assert tool["name"] == stem, "Tool name '{}' doesn't match source_file stem '{}' in {}".format(
                    tool["name"], stem, skill_name
                )


# ---------------------------------------------------------------------------
# TestApiAllConsistency
# ---------------------------------------------------------------------------


class TestApiAllConsistency:
    """Verify api.__all__ is consistent with the symbols it exports."""

    def test_all_exported_symbols_callable_or_class(self):
        from dcc_mcp_maya import api

        for name in api.__all__:
            assert hasattr(api, name), "'{}' in __all__ but not found in api module".format(name)
            obj = getattr(api, name)
            assert callable(obj) or isinstance(obj, type), "'{}' should be callable or a class".format(name)

    def test_maya_warning_in_api_all_and_callable(self):
        from dcc_mcp_maya import api

        assert "maya_warning" in api.__all__
        assert callable(api.maya_warning)

    def test_package_all_superset_of_api_all(self):
        """dcc_mcp_maya.__all__ should include every entry in api.__all__ except MayaCmds."""
        import dcc_mcp_maya
        from dcc_mcp_maya import api

        excluded = {"MayaCmds"}
        for name in api.__all__:
            if name not in excluded:
                assert name in dcc_mcp_maya.__all__, "'{}' in api.__all__ but missing from dcc_mcp_maya.__all__".format(
                    name
                )
