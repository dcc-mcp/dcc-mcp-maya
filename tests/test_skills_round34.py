"""Round 34 — maya_warning helper + SKILL.md tools/groups field validation.

Covers:
- maya_warning(): success=True with context["warning"] key
- maya_warning imported from dcc_mcp_maya top-level package
- maya_warning in api.__all__
- SKILL.md tools: field structure (name + optional annotation hints)
- SKILL.md groups: field structure (name + tools list)
- 4 updated SKILL.md files contain valid tools and groups arrays
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
    """Validate tools/groups metadata for the 4 updated skills.

    As of the dcc-mcp-core 0.15 / #356 sibling-file migration, the
    ``tools:`` and ``groups:`` blocks no longer live inline in
    ``SKILL.md``. They are referenced from ``metadata.dcc-mcp.tools``
    and ``metadata.dcc-mcp.groups`` and carried by sibling
    ``tools.yaml`` / ``groups.yaml`` files next to ``SKILL.md``. These
    tests therefore resolve the sibling files before asserting shape.
    """

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

    def _dcc_mcp_meta(self, frontmatter):
        """Return the ``metadata.dcc-mcp`` mapping (supports flat + nested)."""
        meta = frontmatter.get("metadata") or {}
        nested = meta.get("dcc-mcp")
        if isinstance(nested, dict):
            return nested
        flat = {}
        for key, value in meta.items():
            if isinstance(key, str) and key.startswith("dcc-mcp."):
                flat[key[len("dcc-mcp.") :]] = value
        return flat

    def _load_tools(self, skill_name):
        """Return the tools list from the sibling file referenced by metadata."""
        # Import third-party modules
        import yaml

        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        dcc_mcp = self._dcc_mcp_meta(fm)
        tools_ref = dcc_mcp.get("tools")
        assert isinstance(tools_ref, str) and tools_ref, (
            "metadata.dcc-mcp.tools must be a sibling-file reference in {}".format(skill_name)
        )
        tools_path = os.path.join(SKILLS_DIR, skill_name, tools_ref)
        assert os.path.exists(tools_path), "sibling tools file missing: {}".format(tools_path)
        with open(tools_path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        return doc.get("tools") or []

    def _load_groups(self, skill_name):
        """Return the groups list from the sibling file referenced by metadata.

        ``groups`` may live in ``groups.yaml`` or be co-located inside
        ``tools.yaml`` (both are accepted by dcc-mcp-core).
        """
        # Import third-party modules
        import yaml

        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        dcc_mcp = self._dcc_mcp_meta(fm)
        groups_ref = dcc_mcp.get("groups")
        if isinstance(groups_ref, str) and groups_ref:
            groups_path = os.path.join(SKILLS_DIR, skill_name, groups_ref)
            assert os.path.exists(groups_path), "sibling groups file missing: {}".format(groups_path)
            with open(groups_path, encoding="utf-8") as fh:
                doc = yaml.safe_load(fh) or {}
            return doc.get("groups") or []
        # Fallback: groups declared inline in tools.yaml
        tools_ref = dcc_mcp.get("tools")
        if isinstance(tools_ref, str) and tools_ref:
            tools_path = os.path.join(SKILLS_DIR, skill_name, tools_ref)
            if os.path.exists(tools_path):
                with open(tools_path, encoding="utf-8") as fh:
                    doc = yaml.safe_load(fh) or {}
                return doc.get("groups") or []
        return []

    def _tool_hint(self, tool, key):
        """Fetch an annotation hint from either the flat or nested form."""
        if key in tool:
            return tool[key]
        ann = tool.get("annotations")
        if isinstance(ann, dict):
            return ann.get(key)
        return None

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_tools_key_present(self, skill_name):
        content = self._read_skill_md(skill_name)
        fm = self._parse_frontmatter(content)
        dcc_mcp = self._dcc_mcp_meta(fm)
        assert "tools" in dcc_mcp, "metadata.dcc-mcp.tools missing in {}".format(skill_name)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_tools_is_list(self, skill_name):
        tools = self._load_tools(skill_name)
        assert isinstance(tools, list), "tools: must be a list in {}".format(skill_name)
        assert len(tools) > 0, "tools: list must not be empty in {}".format(skill_name)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_each_tool_has_required_fields(self, skill_name):
        """Each tool entry must have at least 'name'; 'description' is optional but encouraged."""
        for tool in self._load_tools(skill_name):
            assert "name" in tool, "tool missing 'name' in {}".format(skill_name)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_tool_annotations_present(self, skill_name):
        """Annotation hints must be bool (regardless of flat vs nested form)."""
        for tool in self._load_tools(skill_name):
            for hint in ("read_only_hint", "destructive_hint", "idempotent_hint"):
                value = self._tool_hint(tool, hint)
                if value is not None:
                    assert isinstance(value, bool), "tool '{}' {} must be bool in {}".format(
                        tool.get("name", "?"), hint, skill_name
                    )

    @pytest.mark.parametrize("skill_name", SKILL_NAMES_WITH_TOOLS)
    def test_groups_key_present(self, skill_name):
        """Each skill with tools should define at least one group."""
        groups = self._load_groups(skill_name)
        assert isinstance(groups, list), "groups: must be a list in {}".format(skill_name)
        assert len(groups) > 0, "groups: list must not be empty in {}".format(skill_name)
        for group in groups:
            assert "name" in group, "group missing 'name' in {}".format(skill_name)
            assert "tools" in group, "group missing 'tools' in {}".format(skill_name)

    def test_maya_scene_tool_count(self):
        assert len(self._load_tools("maya-scene")) >= 8

    def test_maya_primitives_tool_count(self):
        assert len(self._load_tools("maya-primitives")) == 8

    def test_maya_animation_tool_count(self):
        assert len(self._load_tools("maya-animation")) >= 7

    def test_maya_render_tool_count(self):
        assert len(self._load_tools("maya-render")) >= 8

    def test_readonly_tools_not_destructive(self):
        """read_only_hint=True tools should not be destructive."""
        for skill_name in SKILL_NAMES_WITH_TOOLS:
            for tool in self._load_tools(skill_name):
                if self._tool_hint(tool, "read_only_hint") is True:
                    assert self._tool_hint(tool, "destructive_hint") is not True, (
                        "read_only_hint tool '{}' in {} should not be destructive_hint".format(
                            tool.get("name"), skill_name
                        )
                    )

    def test_group_tools_subset_of_skill_tools(self):
        """Every tool listed in a group must exist in the skill's tools list."""
        for skill_name in SKILL_NAMES_WITH_TOOLS:
            tool_names = {t["name"] for t in self._load_tools(skill_name)}
            for group in self._load_groups(skill_name):
                for t in group["tools"]:
                    assert t in tool_names, "group '{}' references tool '{}' not in tools list of {}".format(
                        group["name"], t, skill_name
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
