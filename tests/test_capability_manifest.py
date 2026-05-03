"""Unit tests for :mod:`dcc_mcp_maya.capability_manifest` (issue #163).

These tests verify the SOLID projection from live catalog state into a
compact gateway-friendly manifest — the core #163 deliverable on the
Maya adapter side.

Scenarios covered:

* Empty catalog => empty records list, metadata still well-formed.
* Mixed loaded / unloaded skills => ``totals`` and per-record ``loaded``
  fields are correct.
* Skill stubs (``__skill__xxx`` / ``__group__xxx``) are filtered out so
  they never flood the gateway index.
* Long summaries are truncated to 240 chars to keep the token budget
  tight (the core capability index advertises ~200 B / record).
* Tags from action + parent skill + group are de-duplicated.
* ``register_capability_mcp_tool`` successfully wires a handler on a
  duck-typed server — and the emitted payload is addressable from an
  AI agent without spawning subprocesses.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

from dcc_mcp_maya.capability_manifest import (
    CapabilityRecord,
    MayaCapabilityManifestBuilder,
    build_manifest_payload,
    register_capability_mcp_tool,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _action(
    name: str,
    *,
    skill: str = None,
    summary: str = "",
    tags: List[str] = None,
    execution: str = "sync",
    affinity: str = "main",
    timeout_hint_secs: int = None,
    input_schema: Dict[str, Any] = None,
    group: str = None,
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {"name": name}
    if skill is not None:
        entry["skill"] = skill
    if summary:
        entry["summary"] = summary
    if tags is not None:
        entry["tags"] = tags
    if execution:
        entry["execution"] = execution
    if affinity:
        entry["affinity"] = affinity
    if timeout_hint_secs is not None:
        entry["timeout_hint_secs"] = timeout_hint_secs
    if input_schema is not None:
        entry["input_schema"] = input_schema
    if group:
        entry["group"] = group
    return entry


def _skill(name: str, *, tags: List[str] = None, summary: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"name": name}
    if tags is not None:
        out["tags"] = tags
    if summary:
        out["summary"] = summary
    return out


# ---------------------------------------------------------------------------
# Builder — empty catalog
# ---------------------------------------------------------------------------


def test_builder_empty_catalog_returns_empty_records():
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: [],
        action_lister=lambda: [],
        is_loaded=lambda _: False,
    )
    assert builder.build() == []


def test_builder_tolerates_missing_lister_callables():
    # When no injection is provided, the builder must still return a list
    # (empty) instead of raising — used during bootstrap before the
    # catalog has finished initialising.
    builder = MayaCapabilityManifestBuilder()
    assert builder.build() == []


# ---------------------------------------------------------------------------
# Builder — typical catalog
# ---------------------------------------------------------------------------


def test_builder_projects_loaded_and_unloaded_actions():
    actions = [
        _action(
            "maya_scene__new_scene",
            skill="maya-scene",
            summary="Create a new empty Maya scene",
            tags=["scene"],
            input_schema={"type": "object"},
        ),
        _action(
            "maya_scripting__execute_python",
            skill="maya-scripting",
            summary="Run arbitrary Python in Maya's interpreter",
            tags=["python"],
            execution="async",
            timeout_hint_secs=120,
            input_schema={"type": "object", "properties": {"code": {"type": "string"}}},
        ),
        _action(
            "maya_render__render_frames",
            skill="maya-render",
            summary="Render a frame range",
            tags=["render"],
            execution="async",
            timeout_hint_secs=600,
        ),
    ]
    skills = [
        _skill("maya-scene", tags=["scene", "io"]),
        _skill("maya-scripting", tags=["scripting"]),
        _skill("maya-render", tags=["render"]),
    ]
    loaded = {"maya-scene", "maya-scripting"}

    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: skills,
        action_lister=lambda: actions,
        is_loaded=lambda name: name in loaded,
    )
    records = builder.build()

    assert len(records) == 3
    by_name = {r.backend_tool: r for r in records}

    # Loaded skills project the loaded flag correctly.
    assert by_name["maya_scene__new_scene"].loaded is True
    assert by_name["maya_scripting__execute_python"].loaded is True
    assert by_name["maya_render__render_frames"].loaded is False

    # Tags union action + skill.
    assert set(by_name["maya_scene__new_scene"].tags) >= {"scene", "io"}

    # Execution metadata propagates.
    rec = by_name["maya_scripting__execute_python"]
    assert rec.execution == "async"
    assert rec.timeout_hint_secs == 120
    assert rec.has_schema is True

    # tool_slug has the expected shape.
    assert rec.tool_slug == "maya.instance.maya_scripting__execute_python"


def test_builder_drops_skill_and_group_stubs():
    actions = [
        _action("maya_scene__new_scene", skill="maya-scene"),
        _action("__skill__maya_render", skill="maya-render"),
        _action("__group__maya-render.extended", skill="maya-render"),
    ]
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: [_skill("maya-scene")],
        action_lister=lambda: actions,
        is_loaded=lambda _: False,
    )
    records = builder.build()
    assert [r.backend_tool for r in records] == ["maya_scene__new_scene"]


def test_builder_truncates_long_summary():
    long = "x" * 500
    actions = [_action("maya_scene__new_scene", skill="maya-scene", summary=long)]
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: [_skill("maya-scene")],
        action_lister=lambda: actions,
        is_loaded=lambda _: True,
    )
    record = builder.build()[0]
    # Cap must be 200 chars including the ellipsis — token-budget guard.
    assert len(record.summary) <= 200
    assert record.summary.endswith("…")


def test_builder_survives_lister_exceptions():
    def boom():
        raise RuntimeError("catalog broken")

    builder = MayaCapabilityManifestBuilder(
        skill_lister=boom,
        action_lister=boom,
        is_loaded=lambda _: False,
    )
    assert builder.build() == []


def test_builder_infers_skill_from_tool_name_convention():
    # Action dicts emitted by some catalogs omit ``skill`` — we fall back to
    # the standard ``{skill}__{script}`` convention.
    actions = [_action("maya_scene__new_scene")]
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: [],
        action_lister=lambda: actions,
        is_loaded=lambda _: False,
    )
    record = builder.build()[0]
    assert record.skill_name == "maya-scene"


# ---------------------------------------------------------------------------
# CapabilityRecord.to_dict — minimises token usage
# ---------------------------------------------------------------------------


def test_capability_record_to_dict_omits_empty_optional_fields():
    rec = CapabilityRecord(
        tool_slug="maya.instance.maya_scene__new_scene",
        backend_tool="maya_scene__new_scene",
        skill_name="maya-scene",
        summary="",
        loaded=False,
    )
    dumped = rec.to_dict()
    # Empty summary / empty tags / None execution must be dropped.
    assert "summary" not in dumped
    assert "tags" not in dumped
    assert "execution" not in dumped
    assert dumped["backend_tool"] == "maya_scene__new_scene"
    assert dumped["loaded"] is False  # False kept — it's a meaningful value


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------


def test_build_manifest_payload_headers_and_totals():
    records = [
        CapabilityRecord(
            tool_slug="maya.instance.a",
            backend_tool="a",
            skill_name="s1",
            summary="",
            loaded=True,
        ),
        CapabilityRecord(
            tool_slug="maya.instance.b",
            backend_tool="b",
            skill_name="s2",
            summary="",
            loaded=False,
        ),
    ]
    payload = build_manifest_payload(
        records,
        dcc_version="2025",
        scene="/a.ma",
        instance_id="abc123",
        display_name="Maya 2025 — a.ma",
    )
    assert payload["schema_version"] == "1"
    assert payload["dcc_type"] == "maya"
    assert payload["metadata"]["instance_id"] == "abc123"
    assert payload["metadata"]["scene"] == "/a.ma"
    assert payload["metadata"]["dcc_version"] == "2025"
    assert payload["totals"] == {
        "actions": 2,
        "loaded_actions": 1,
        "unloaded_actions": 1,
        "skills": 2,
        "loaded_skills": 1,
        "unloaded_skills": 1,
    }
    assert len(payload["capabilities"]) == 2


def test_build_manifest_payload_strips_none_metadata():
    payload = build_manifest_payload([], dcc_version=None, scene="", instance_id=None)
    # None / empty-string values dropped — keeps the gateway payload compact.
    assert "dcc_version" not in payload["metadata"]
    assert "scene" not in payload["metadata"]
    assert "instance_id" not in payload["metadata"]


# ---------------------------------------------------------------------------
# MCP tool registration (no server side-effects — duck-typed inner)
# ---------------------------------------------------------------------------


class _FakeRegistry:
    def __init__(self):
        self.registered: List[tuple] = []

    def register(self, name, **kwargs):
        self.registered.append((name, kwargs))


class _FakeInner:
    """Duck-typed ``DccServerBase._server`` for MCP registration assertions."""

    def __init__(self):
        self.registry = _FakeRegistry()
        self.handlers: Dict[str, Any] = {}

    def register_handler(self, name: str, handler):
        self.handlers[name] = handler


def test_register_capability_mcp_tool_returns_manifest_via_handler():
    inner = _FakeInner()
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: [_skill("maya-scene")],
        action_lister=lambda: [_action("maya_scene__new_scene", skill="maya-scene")],
        is_loaded=lambda _: True,
    )
    fake_server = MagicMock()
    fake_server._server = inner
    fake_server._config = MagicMock(scene="/p/a.ma", dcc_version="2025")

    ok = register_capability_mcp_tool(fake_server, builder=builder)
    assert ok is True
    assert "dcc_capability_manifest" in inner.handlers
    # Registry must also carry the declaration so MCP tools/list picks it up.
    declared = [name for name, _ in inner.registry.registered]
    assert "dcc_capability_manifest" in declared

    # Invoke the handler and validate the envelope.
    result = inner.handlers["dcc_capability_manifest"]({})
    assert result["success"] is True
    assert result["context"]["totals"]["loaded_actions"] == 1
    assert result["context"]["capabilities"][0]["backend_tool"] == "maya_scene__new_scene"


# ---------------------------------------------------------------------------
# Unloaded-skill projection (issue #174)
# ---------------------------------------------------------------------------


def test_builder_projects_unloaded_skills_with_load_hint():
    """Unloaded skills contribute records with load hints and requires_load_skill."""
    actions = [_action("maya_scene__new_scene", skill="maya-scene")]
    skills = [_skill("maya-scene"), _skill("maya-geometry", tags=["mesh"])]
    skill_info_map = {
        "maya-geometry": {
            "tags": ["mesh"],
            "tools": [
                {
                    "name": "create_sphere",
                    "description": "Create a polygon sphere in the current Maya scene.",
                    "execution": "sync",
                    "group": "geometry",
                    "input_schema": {"type": "object", "properties": {"radius": {"type": "number"}}},
                },
                {
                    "name": "file_exists",
                    "description": "Check whether a file exists on disk.",
                    "execution": "sync",
                    "group": "core",
                    "input_schema": {"type": "object"},
                },
                # Stubs must never leak into user-visible capabilities.
                {"name": "__skill__maya-geometry"},
            ],
        },
    }

    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: skills,
        action_lister=lambda: actions,
        is_loaded=lambda name: name == "maya-scene",
        skill_info_lister=lambda name: skill_info_map.get(name),
    )

    records = builder.build()
    by_tool = {r.backend_tool: r for r in records}

    assert by_tool["maya_scene__new_scene"].loaded is True
    assert by_tool["maya_scene__new_scene"].requires_load_skill is False
    assert by_tool["maya_scene__new_scene"].load_hint == {}

    sphere = by_tool["maya_geometry__create_sphere"]
    assert sphere.loaded is False
    assert sphere.requires_load_skill is True
    assert sphere.load_hint == {
        "tool": "load_skill",
        "arguments": {"skill_name": "maya-geometry"},
    }
    assert sphere.callable_id == "maya_geometry__create_sphere"
    assert "mesh" in sphere.tags
    assert sphere.has_schema is True

    # to_dict() preserves requires_load_skill for unloaded records but
    # strips the duplicate callable_id (since it equals backend_tool).
    sphere_dict = sphere.to_dict()
    assert sphere_dict["requires_load_skill"] is True
    assert "callable_id" not in sphere_dict
    assert sphere_dict["load_hint"] == {
        "tool": "load_skill",
        "arguments": {"skill_name": "maya-geometry"},
    }

    exists = by_tool["maya_geometry__file_exists"]
    assert exists.requires_load_skill is True
    assert exists.group == "core"

    # __skill__* stub never produces a capability.
    assert not any(r.backend_tool.startswith("__skill__") for r in records)


def test_manifest_totals_report_unloaded_counts():
    actions = [_action("maya_scene__new_scene", skill="maya-scene")]
    skills = [_skill("maya-scene"), _skill("maya-render"), _skill("maya-geometry")]
    skill_info_map = {
        "maya-render": {
            "tools": [
                {"name": "render_frames", "execution": "async", "timeout_hint_secs": 600},
            ],
        },
        "maya-geometry": {
            "tools": [
                {"name": "create_sphere", "execution": "sync"},
                {"name": "file_exists", "execution": "sync"},
            ],
        },
    }
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: skills,
        action_lister=lambda: actions,
        is_loaded=lambda name: name == "maya-scene",
        skill_info_lister=lambda name: skill_info_map.get(name),
    )
    payload = build_manifest_payload(builder.build())
    assert payload["totals"]["loaded_actions"] == 1
    assert payload["totals"]["unloaded_actions"] == 3
    assert payload["totals"]["unloaded_skills"] == 2


def test_unloaded_records_preserve_callable_id_exact_match():
    """Callable id must round-trip to ``{skill_snake}__{tool}`` for gateway routing."""
    skills = [_skill("maya-geometry")]
    skill_info_map = {
        "maya-geometry": {"tools": [{"name": "export_fbx", "execution": "async", "timeout_hint_secs": 300}]},
    }
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: skills,
        action_lister=lambda: [],
        is_loaded=lambda _: False,
        skill_info_lister=lambda name: skill_info_map.get(name),
    )
    records = builder.build()
    assert len(records) == 1
    record = records[0]
    assert record.callable_id == "maya_geometry__export_fbx"
    assert record.backend_tool == "maya_geometry__export_fbx"
    assert record.tool_slug == "maya.instance.maya_geometry__export_fbx"
    assert record.load_hint["arguments"]["skill_name"] == "maya-geometry"
    # Serialisation keeps load_hint but drops the duplicate callable_id to
    # respect the 640 B / record manifest budget.
    dumped = record.to_dict()
    assert dumped["load_hint"]["arguments"]["skill_name"] == "maya-geometry"
    assert "callable_id" not in dumped


def test_register_capability_mcp_tool_honours_loaded_only_param():
    inner = _FakeInner()
    builder = MayaCapabilityManifestBuilder(
        skill_lister=lambda: [_skill("maya-scene"), _skill("maya-render")],
        action_lister=lambda: [
            _action("maya_scene__new_scene", skill="maya-scene"),
            _action("maya_render__render_frames", skill="maya-render"),
        ],
        is_loaded=lambda name: name == "maya-scene",
    )
    fake_server = MagicMock()
    fake_server._server = inner
    fake_server._config = MagicMock(scene=None, dcc_version="2025")

    register_capability_mcp_tool(fake_server, builder=builder)
    handler = inner.handlers["dcc_capability_manifest"]

    full = handler({})["context"]
    subset = handler({"loaded_only": True})["context"]

    assert full["totals"]["actions"] == 2
    assert subset["totals"]["actions"] == 1
    assert subset["capabilities"][0]["skill_name"] == "maya-scene"


def test_register_capability_mcp_tool_missing_inner_returns_false():
    fake_server = MagicMock()
    fake_server._server = None
    builder = MayaCapabilityManifestBuilder()
    assert register_capability_mcp_tool(fake_server, builder=builder) is False
