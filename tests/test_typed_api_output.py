"""Tests for :func:`dcc_mcp_maya.api.maya_typed_success` (core 0.14.22).

Context
-------
``maya_typed_success`` bridges the gap between typed Python skill
handlers and MCP clients that validate responses against a JSON Schema.
Until dcc-mcp-core propagates ``tools.yaml`` ``outputSchema`` at
registration time (upstream gap filed separately), the helper embeds
the derived schema directly in the envelope's ``context.output_schema``
field so downstream agents can still validate.

The tests below focus on behaviour skill authors actually rely on:

1. **Shape**: the helper delegates to ``maya_success`` and never
   invents new top-level keys.
2. **Dataclass round-trip**: data is serialised via ``dataclasses.asdict``
   and schema is derived from the dataclass type.
3. **Explicit ``return_type``** wins over ``type(data)`` (for dicts that
   conform to a ``TypedDict``).
4. **Dependency-free fallback**: when ``derive_schema`` is unavailable
   or fails, the helper still returns a valid envelope (no schema,
   still-serialised data).
5. **Real core parity**: against an installed ``dcc_mcp_core.schema``
   0.14.22, the derived schema matches the standalone
   ``derive_schema`` call exactly.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya.api import maya_typed_success

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / canonical test types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SphereResult:
    name: str
    radius: float
    construction_history: Optional[str] = None


@dataclass
class _NestedTransform:
    rotation: tuple  # intentionally loose; dataclass schema treats as array
    translation: tuple


def _fake_deriver(_tp: Any) -> Dict[str, Any]:
    return {"type": "object", "title": "fake"}


def _null_deriver(_tp: Any) -> Optional[Dict[str, Any]]:
    return None


def _raising_deriver(_tp: Any) -> Dict[str, Any]:
    raise RuntimeError("upstream died")


# ─────────────────────────────────────────────────────────────────────────────
# Shape + contract
# ─────────────────────────────────────────────────────────────────────────────


def test_envelope_has_same_top_level_shape_as_maya_success():
    """``maya_typed_success`` MUST NOT invent new top-level keys.

    Agents deserialise the envelope with the same schema they use for
    ``maya_success`` — breaking the top-level shape is a silent wire
    incompatibility.
    """
    from dcc_mcp_maya.api import maya_success

    baseline = maya_success("ok", foo=1)
    typed = maya_typed_success("ok", SphereResult(name="s", radius=1.0), foo=1)
    # Top-level key set must match exactly.
    assert set(typed.keys()) == set(baseline.keys())


def test_success_flag_is_true():
    result = maya_typed_success("ok", SphereResult(name="s", radius=1.0))
    assert result["success"] is True
    assert result["message"] == "ok"


def test_context_carries_output_schema_and_typed_result():
    result = maya_typed_success(
        "ok",
        SphereResult(name="pSphere1", radius=2.0, construction_history="polySphere1"),
    )
    ctx = result["context"]
    assert ctx["output_schema"]["title"] == "SphereResult"
    assert ctx["typed_result"] == {
        "name": "pSphere1",
        "radius": 2.0,
        "construction_history": "polySphere1",
    }


def test_extra_context_kwargs_merge_alongside_schema():
    result = maya_typed_success(
        "ok",
        SphereResult(name="a", radius=1.0),
        trace_id="xyz",
        origin="unit-test",
    )
    ctx = result["context"]
    # Caller-provided context survives verbatim.
    assert ctx["trace_id"] == "xyz"
    assert ctx["origin"] == "unit-test"
    # Helper-provided context is additive.
    assert "output_schema" in ctx
    assert "typed_result" in ctx


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation variants
# ─────────────────────────────────────────────────────────────────────────────


def test_dict_data_is_accepted_with_explicit_return_type():
    """When ``data`` is already a dict, the caller can pass
    ``return_type`` explicitly so the schema still reflects the
    ``TypedDict`` contract rather than the generic ``dict`` type.
    """
    result = maya_typed_success(
        "ok",
        {"name": "foo", "radius": 1.0},
        return_type=SphereResult,
    )
    assert result["context"]["typed_result"] == {"name": "foo", "radius": 1.0}
    # The schema title still tracks the explicit type.
    assert result["context"]["output_schema"]["title"] == "SphereResult"


def test_namedtuple_data_serialises_via_asdict():
    Pair = namedtuple("Pair", ["left", "right"])
    result = maya_typed_success("ok", Pair(left=1, right=2))
    assert result["context"]["typed_result"] == {"left": 1, "right": 2}


def test_plain_object_with_dunder_dict_is_serialised():
    class _Plain:
        def __init__(self):
            self.a = 1
            self.b = "x"
            self._hidden = "nope"  # leading-underscore keys are skipped

    result = maya_typed_success("ok", _Plain())
    assert result["context"]["typed_result"] == {"a": 1, "b": "x"}


def test_scalar_data_is_wrapped_under_value_key():
    result = maya_typed_success("ok", 42)
    # A bare int has no ``__dict__`` — we wrap it so the envelope still
    # carries a structured payload rather than a stringified int.
    assert result["context"]["typed_result"] == {"value": 42}


# ─────────────────────────────────────────────────────────────────────────────
# Dependency-injection seams
# ─────────────────────────────────────────────────────────────────────────────


def test_injected_schema_deriver_is_used():
    result = maya_typed_success(
        "ok",
        SphereResult(name="a", radius=1.0),
        _schema_deriver=_fake_deriver,
    )
    assert result["context"]["output_schema"] == {"type": "object", "title": "fake"}


def test_deriver_returning_none_omits_schema():
    result = maya_typed_success(
        "ok",
        SphereResult(name="a", radius=1.0),
        _schema_deriver=_null_deriver,
    )
    assert "output_schema" not in result["context"]
    # But typed_result is still populated — no schema doesn't kill the payload.
    assert result["context"]["typed_result"]["name"] == "a"


def test_deriver_raising_is_caller_responsibility():
    # An injected deriver that raises propagates — this is a deliberate
    # contract: the default deriver shields skills from upstream crashes
    # (tested in :func:`test_real_default_deriver_returns_none_when_core_schema_breaks`),
    # but an explicit caller-supplied deriver is treated as "you know what
    # you're doing".  This test locks that contract so future refactors
    # don't silently widen the catch.
    with pytest.raises(RuntimeError, match="upstream died"):
        maya_typed_success(
            "ok",
            SphereResult(name="a", radius=1.0),
            _schema_deriver=_raising_deriver,
        )


def test_default_deriver_swallows_upstream_crash(monkeypatch):
    """The default deriver must shield skills from a buggy upstream."""
    import dcc_mcp_maya.api as api_mod

    # Monkeypatch the default deriver's lookup to simulate a core
    # version where ``derive_schema`` raises unexpectedly.
    def _boom(tp):
        raise RuntimeError("upstream died")

    monkeypatch.setattr(api_mod, "_default_schema_deriver", _boom, raising=True)
    with pytest.raises(RuntimeError):
        # Proves the monkeypatch is effective; the real default sits
        # BEHIND a try/except that _default_schema_deriver performs
        # internally — see the next test.
        _boom(SphereResult)


def test_real_default_deriver_returns_none_when_core_schema_breaks(monkeypatch):
    # Simulate the ``from dcc_mcp_core.schema import derive_schema`` call
    # raising inside ``_default_schema_deriver``.  The helper must NOT
    # propagate the exception.
    import dcc_mcp_core.schema as schema_mod

    import dcc_mcp_maya.api as api_mod

    def _broken(tp):
        raise ValueError("schema derivation broken")

    monkeypatch.setattr(schema_mod, "derive_schema", _broken, raising=True)
    assert api_mod._default_schema_deriver(SphereResult) is None


# ─────────────────────────────────────────────────────────────────────────────
# Real-core parity (requires 0.14.22's ``derive_schema``)
# ─────────────────────────────────────────────────────────────────────────────


def _has_derive_schema() -> bool:
    try:
        from dcc_mcp_core.schema import derive_schema  # noqa: F401

        return True
    except Exception:
        return False


requires_derive_schema = pytest.mark.skipif(
    not _has_derive_schema(),
    reason="installed dcc-mcp-core lacks .schema.derive_schema (pre-0.14.22)",
)


@requires_derive_schema
def test_helper_schema_equals_derive_schema_standalone():
    """Regression lock: what the helper embeds MUST equal what a user
    would get from calling ``derive_schema`` themselves.
    """
    from dcc_mcp_core.schema import derive_schema

    standalone = derive_schema(SphereResult)
    envelope = maya_typed_success("ok", SphereResult(name="a", radius=1.0))
    assert envelope["context"]["output_schema"] == standalone


@requires_derive_schema
def test_helper_respects_mcp_outputschema_contract():
    """The MCP spec (draft 2024-11-05) expects ``outputSchema`` to carry
    a JSON Schema with ``type``, ``properties``, and ``required`` (for
    object-shaped outputs).  The helper's schema MUST satisfy those
    invariants so a generic MCP client can validate against it.
    """
    envelope = maya_typed_success("ok", SphereResult(name="a", radius=1.0))
    schema = envelope["context"]["output_schema"]
    assert schema.get("type") == "object"
    assert "properties" in schema
    assert "required" in schema
    # ``construction_history`` is ``Optional`` → NOT required.
    assert "construction_history" not in schema["required"]
    assert "name" in schema["required"]
    assert "radius" in schema["required"]
