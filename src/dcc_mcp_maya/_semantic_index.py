"""Optional morphology-aware semantic skill recall (issue #313).

``MayaMcpServer.search_skills`` routes through the Rust BM25-lite scorer in
``dcc-mcp-skills``. That path is excellent for exact / tokenised queries but
misses morphology variants a natural-language MCP agent commonly produces —
``"rendering the active frame"`` does not tokenise to the literal ``render``
token in the ``maya-render`` skill's name / summary.

This module fuses the Python-side ``VectorSkillIndex`` (``HashedEmbedder``
char-3-gram defaults, zero runtime deps) with a ``LexicalSkillIndex`` through
``RrfFusionIndex`` (Cormack et al. 2009, RRF k=60). The fused index is used
**only to augment** the canonical base results: base ordering is preserved
verbatim (so queries that already worked under BM25 never get demoted) and
vector-only recalls are appended afterwards.

The whole feature is gated behind ``DCC_MCP_MAYA_SEMANTIC_INDEX=1`` so the
default behaviour is byte-for-byte unchanged for the first release. When the
optional ``dcc-mcp-core[semantic]`` extra is installed,
``DCC_MCP_MAYA_SEMANTIC_EMBEDDER=onnx`` swaps ``HashedEmbedder`` for the real
dense ``OnnxEmbedder`` without touching any call site.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional, Sequence

logger = logging.getLogger(__name__)

#: Enable the lexical+vector fusion augmentation. Default off.
ENV_SEMANTIC_INDEX = "DCC_MCP_MAYA_SEMANTIC_INDEX"
#: ``hashed`` (default, zero-dep) or ``onnx`` (requires the ``[semantic]`` extra).
ENV_SEMANTIC_EMBEDDER = "DCC_MCP_MAYA_SEMANTIC_EMBEDDER"

_TRUTHY = ("1", "true", "yes", "on")


def resolve_semantic_index_enabled(env: Optional[dict] = None) -> bool:
    """Return ``True`` when ``DCC_MCP_MAYA_SEMANTIC_INDEX`` is truthy."""
    environ = env if env is not None else os.environ
    return str(environ.get(ENV_SEMANTIC_INDEX, "")).strip().lower() in _TRUTHY


def resolve_embedder_kind(env: Optional[dict] = None) -> str:
    """Return the requested embedder kind: ``"hashed"`` (default) or ``"onnx"``."""
    environ = env if env is not None else os.environ
    kind = str(environ.get(ENV_SEMANTIC_EMBEDDER, "hashed")).strip().lower()
    return "onnx" if kind == "onnx" else "hashed"


def _summary_text(summary: Any) -> str:
    """Best-effort description string from a ``SkillSummary``-like object."""
    parts = []
    for attr in ("description", "search_hint"):
        value = getattr(summary, attr, "") or ""
        if value and value not in parts:
            parts.append(str(value))
    return " ".join(parts)


def _summary_name(summary: Any) -> Optional[str]:
    name = getattr(summary, "name", None)
    return str(name) if name else None


def _build_embedder(kind: str) -> Any:
    """Construct the requested embedder, falling back to ``HashedEmbedder``.

    ``OnnxEmbedder`` raises ``EmbedderError`` when the ``[semantic]`` extra is
    not installed; in that case we degrade to the zero-dep hashed embedder and
    log a warning rather than disabling recall entirely.
    """
    from dcc_mcp_core import HashedEmbedder  # noqa: PLC0415

    if kind != "onnx":
        return HashedEmbedder()
    try:
        from dcc_mcp_core import OnnxEmbedder  # noqa: PLC0415

        return OnnxEmbedder()
    except Exception as exc:  # noqa: BLE001 — EmbedderError / ImportError
        logger.warning(
            "[maya] DCC_MCP_MAYA_SEMANTIC_EMBEDDER=onnx requested but unavailable "
            "(%s); falling back to HashedEmbedder. Install dcc-mcp-core[semantic].",
            exc,
        )
        return HashedEmbedder()


class MayaSemanticIndex:
    """Lexical + vector fusion index used to augment base ``search_skills``.

    The index is rebuilt lazily whenever the catalogue's skill set changes
    (cheap for the adapter's ~25 skills — sub-millisecond per query).
    """

    def __init__(self, fusion: Any, embedder_kind: str) -> None:
        self._fusion = fusion
        self.embedder_kind = embedder_kind
        self._signature: Optional[frozenset] = None

    # ── construction ────────────────────────────────────────────────────
    @classmethod
    def build(cls, *, embedder_kind: Optional[str] = None) -> Optional["MayaSemanticIndex"]:
        """Build the fused index, or ``None`` when core lacks the semantic API."""
        try:
            from dcc_mcp_core import LexicalSkillIndex, RrfFusionIndex, VectorSkillIndex  # noqa: PLC0415
        except Exception as exc:  # noqa: BLE001 — older core without #1393
            logger.info(
                "[maya] semantic index requested but dcc-mcp-core lacks "
                "VectorSkillIndex (%s); needs dcc-mcp-core>=0.17.38.",
                exc,
            )
            return None
        kind = embedder_kind or resolve_embedder_kind()
        try:
            fusion = (
                RrfFusionIndex()
                .register("lex", LexicalSkillIndex())
                .register("vec", VectorSkillIndex(embedder=_build_embedder(kind)))
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[maya] failed to build semantic fusion index: %s", exc)
            return None
        return cls(fusion, kind)

    # ── indexing / recall ───────────────────────────────────────────────
    def rebuild(self, summaries: Sequence[Any]) -> None:
        """(Re)index ``summaries`` only when the skill set changed."""
        from dcc_mcp_core import SkillDocument  # noqa: PLC0415

        signature = frozenset(
            (n, getattr(s, "version", "")) for s in summaries if (n := _summary_name(s)) is not None
        )
        if signature == self._signature:
            return
        docs = []
        for summary in summaries:
            name = _summary_name(summary)
            if name is None:
                continue
            docs.append(
                SkillDocument(
                    skill_id=name,
                    name=name,
                    summary=_summary_text(summary),
                    tags=tuple(str(t) for t in (getattr(summary, "tags", None) or ())),
                    dcc_name=str(getattr(summary, "dcc", "") or ""),
                )
            )
        self._fusion.clear()
        if docs:
            self._fusion.index(docs)
        self._signature = signature

    def recall(self, query: str, *, k: int = 16) -> List[str]:
        """Return fused-rank ``skill_id``s for ``query`` (best first)."""
        if not query or not str(query).strip():
            return []
        try:
            hits = self._fusion.search(str(query), k=k)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[maya] semantic recall failed for %r: %s", query, exc)
            return []
        return [hit.skill_id for hit in hits]

    # ── fusion / augmentation ───────────────────────────────────────────
    def augment(
        self,
        base: Sequence[Any],
        query: Optional[str],
        all_summaries: Sequence[Any],
        *,
        limit: Optional[int] = None,
    ) -> List[Any]:
        """Append morphology-recalled skills after the canonical ``base`` list.

        ``base`` ordering is preserved verbatim — RRF promotes, never demotes
        (issue #313 acceptance). Skills surfaced only by the vector backend are
        appended in fused-rank order.
        """
        result = list(base)
        if not query or not str(query).strip():
            return result
        try:
            self.rebuild(all_summaries)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[maya] semantic rebuild failed: %s", exc)
            return result

        by_name = {n: s for s in all_summaries if (n := _summary_name(s)) is not None}
        present = {_summary_name(s) for s in result}
        for skill_id in self.recall(query):
            if skill_id in present or skill_id not in by_name:
                continue
            result.append(by_name[skill_id])
            present.add(skill_id)

        if limit is not None and limit >= 0:
            result = result[:limit]
        return result


def build_semantic_index() -> Optional[MayaSemanticIndex]:
    """Return a ready index when the feature is enabled, else ``None``."""
    if not resolve_semantic_index_enabled():
        return None
    return MayaSemanticIndex.build()
