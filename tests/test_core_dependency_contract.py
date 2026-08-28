"""Keep the supported dcc-mcp-core range consistent across release surfaces."""

import re
import unicodedata
from html import unescape
from pathlib import Path
from typing import List
from urllib.parse import unquote

import pytest

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.7-3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
CORE_DECLARATION = re.compile(
    r"dcc-mcp-core(?P<spec>\s*(?:(?:>=|<=|==|~=|!=|>|<)\s*[0-9][0-9A-Za-z.!+_*-]*"
    r"(?:\s*,\s*(?:>=|<=|==|~=|!=|>|<)\s*[0-9][0-9A-Za-z.!+_*-]*)*))"
)
CORE_NAME = re.compile(r"\bdcc-mcp-core\b", re.IGNORECASE)
CORE_PACKAGE_SPELLING = re.compile(r"\bdcc[-_.]+mcp[-_.]+core\b", re.IGNORECASE)
VERSION_CLAIM = re.compile(r"(?<![0-9A-Za-z])\d+(?:[0-9A-Za-z.!+_-]*)(?![0-9A-Za-z])")
DOTTED_VERSION_CLAIM = re.compile(r"\d+(?:\.\d+)+")
MARKDOWN_INLINE_IMAGE = re.compile(
    r"!\[(?P<label>[^\]\r\n]*)\]\((?P<destination>[^\s)\r\n]+)"
    r"(?:[ \t]+(?P<title>\"[^\"\r\n]*\"|'[^'\r\n]*'|\([^\)\r\n]*\)))?[ \t]*\)"
)
MARKDOWN_INLINE_LINK = re.compile(
    r"(?<!!)\[(?P<label>[^\]\r\n]+)\]\((?P<destination>[^\s)\r\n]+)"
    r"(?:[ \t]+(?P<title>\"[^\"\r\n]*\"|'[^'\r\n]*'|\([^\)\r\n]*\)))?[ \t]*\)"
)
MARKDOWN_REFERENCE_IMAGE = re.compile(r"!\[(?P<label>[^\]\r\n]*)\]\[(?P<reference>[^\]\r\n]*)\]")
MARKDOWN_REFERENCE_LINK = re.compile(r"(?<!!)\[(?P<label>[^\]\r\n]+)\]\[(?P<reference>[^\]\r\n]*)\]")
MARKDOWN_REFERENCE_DEFINITION = re.compile(
    r"^[ \t]{0,3}\[(?P<reference>[^\]\r\n]+)\]:[ \t]+(?P<destination>\S+)"
    r"(?:[ \t]+(?P<title>\"[^\"\r\n]*\"|'[^'\r\n]*'|\([^\)\r\n]*\)))?[ \t]*$"
)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HIDDEN_HTML_CONTAINER = re.compile(
    r"<(?P<tag>[A-Za-z][\w:-]*)\b(?=[^>\r\n]*(?:\bhidden\b|"
    r"style[ \t]*=[ \t]*[\"'][^\"']*(?:display[ \t]*:[ \t]*none|visibility[ \t]*:[ \t]*hidden)))"
    r"[^>\r\n]*>[^\r\n]*?</(?P=tag)[ \t]*>",
    re.IGNORECASE,
)
HTML_TAG = re.compile(r"</?[A-Za-z][^>\r\n]*>")
MARKDOWN_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!<>])")
DEPENDENCY_LANGUAGE = re.compile(r"\b(?:requires?|requirement|depends?|dependency|version)\b", re.IGNORECASE)
UNICODE_HYPHENS = str.maketrans({char: "-" for char in "‐‑‒–—−﹣－"})
CONTRACT_SURFACES = (
    "AGENTS.md",
    "README.md",
    "README_zh.md",
    "install.md",
    "llms.txt",
    "llms-full.txt",
    "docs/guide/installation.md",
    "docs/zh/guide/installation.md",
    "skills/dcc-mcp-maya-setup/SKILL.md",
)


def _core_dependency() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return next(dependency for dependency in project["dependencies"] if dependency.startswith("dcc-mcp-core"))


def _normalize_surface(content: str) -> str:
    decoded = unquote(content)
    decoded = HTML_COMMENT.sub("", decoded)
    decoded = unescape(decoded)
    decoded = HIDDEN_HTML_CONTAINER.sub("", decoded)
    definitions = {}
    for line in decoded.splitlines():
        definition = MARKDOWN_REFERENCE_DEFINITION.fullmatch(line)
        if definition is not None:
            reference = " ".join(definition.group("reference").lower().split())
            definitions.setdefault(reference, (definition.group("title") or "").strip("\"'()"))

    def rendered(label: str, title: str = "") -> str:
        return " ".join(part for part in (label.strip("`"), title.strip("\"'()")) if part)

    def render_reference(match) -> str:
        label = match.group("label")
        reference = match.group("reference") or label
        title = definitions.get(" ".join(reference.lower().split()), "")
        return rendered(label, title)

    rendered_lines = []
    for line in decoded.splitlines():
        if MARKDOWN_REFERENCE_DEFINITION.fullmatch(line) is not None:
            continue
        line = MARKDOWN_INLINE_IMAGE.sub(lambda match: rendered(match.group("label"), match.group("title") or ""), line)
        line = MARKDOWN_REFERENCE_IMAGE.sub(render_reference, line)
        line = MARKDOWN_INLINE_LINK.sub(lambda match: rendered(match.group("label"), match.group("title") or ""), line)
        line = MARKDOWN_REFERENCE_LINK.sub(render_reference, line)
        rendered_lines.append(HTML_TAG.sub("", line))
    decoded = "\n".join(rendered_lines)
    decoded = MARKDOWN_ESCAPE.sub(r"\1", decoded)
    decoded = unicodedata.normalize("NFKC", decoded).translate(UNICODE_HYPHENS)
    decoded = decoded.replace("≥", ">=").replace("≤", "<=")
    return CORE_PACKAGE_SPELLING.sub("dcc-mcp-core", decoded)


def _unparsed_core_claims(content: str) -> List[str]:
    claims = []
    for line in content.splitlines():
        names = list(CORE_NAME.finditer(line))
        for index, name in enumerate(names):
            end = names[index + 1].start() if index + 1 < len(names) else len(line)
            segment = line[name.start() : end]
            dependency_language = DEPENDENCY_LANGUAGE.search(segment)
            single_segment_claim = (
                VERSION_CLAIM.search(segment, dependency_language.end()) if dependency_language is not None else None
            )
            has_version_claim = DOTTED_VERSION_CLAIM.search(segment) is not None or single_segment_claim is not None
            is_symbol_reference = segment.startswith("dcc-mcp-core.") and dependency_language is None
            if has_version_claim and not is_symbol_reference and CORE_DECLARATION.match(line, name.start()) is None:
                claims.append(segment.strip())
    return claims


def _assert_surface_contract(relative_path: str, content: str, canonical: str) -> None:
    """Require exactly one canonical Core declaration on a public surface."""
    decoded = _normalize_surface(content)
    unparsed = _unparsed_core_claims(decoded)
    assert not unparsed, f"{relative_path} unparsed Core version claims: {unparsed!r}"
    declarations = ["dcc-mcp-core" + match.group("spec") for match in CORE_DECLARATION.finditer(decoded)]
    assert declarations == [canonical], f"{relative_path} Core declarations: {declarations!r}; expected {[canonical]!r}"


@pytest.mark.parametrize("relative_path", CONTRACT_SURFACES)
def test_core_dependency_contract_matches_package_metadata(relative_path: str) -> None:
    canonical = _core_dependency()
    content = (ROOT / relative_path).read_text(encoding="utf-8")

    _assert_surface_contract(relative_path, content, canonical)


@pytest.mark.parametrize(
    "injected",
    (
        "dcc-mcp-core>=0.19.45,<1.0.0",
        "dcc-mcp-core >= 0.17.31",
        "dcc-mcp-core >= 0.19.45, < 1.0.0",
        "dcc-mcp-core ≥ 0.17.31",
        "[`dcc-mcp-core`](https://github.com/dcc-mcp/dcc-mcp-core) ≥ 0.17.31",
        "[`dcc-mcp-core`][core] >=0.17.31",
        "[`dcc-mcp-core`](https://github.com/dcc-mcp/dcc-mcp-core)\u00a0>=\u00a00.17.31",
        "dcc-mcp-core ＞＝ 0.17.31",
        "dcc‐mcp‐core>=0.17.31",
        "dcc_mcp_core>=0.17.31",
        "dcc-mcp-core version 0.17.31",
        r"dcc\-mcp\-core>=0.17.31",
        "dcc-mcp-core&gt;=0.17.31",
        '[Core](https://github.com/dcc-mcp/dcc-mcp-core "dcc-mcp-core >=0.17.31")',
        "dcc-mcp-core.ReadinessProbe requires Core version 0.17.31",
        "dcc-mcp-core>=0.19.45,<1.0",
    ),
)
def test_surface_contract_rejects_duplicate_or_alternate_dependency_declarations(injected: str) -> None:
    canonical = _core_dependency()
    mutated = f"Current requirement: {canonical}\nContradictory declaration: {injected}\n"

    with pytest.raises(AssertionError):
        _assert_surface_contract("mutated-public-surface.md", mutated, canonical)


@pytest.mark.parametrize(
    "visible_claim",
    (
        "![dcc-mcp-core>=0.17.31](badge.svg)",
        '![Core](badge.svg "dcc-mcp-core>=0.17.31")',
        "![dcc-mcp-core>=0.17.31][core-badge]",
        '![Core][core-badge]\n[core-badge]: badge.svg "dcc-mcp-core>=0.17.31"',
        "`dcc-mcp-core>=0.17.31`",
        "```text\ndcc-mcp-core>=0.17.31\n```",
    ),
)
def test_rendered_markdown_scanner_rejects_visible_core_claims(visible_claim: str) -> None:
    canonical = _core_dependency()
    mutated = "Current requirement: %s\n%s\n" % (canonical, visible_claim)

    with pytest.raises(AssertionError):
        _assert_surface_contract("rendered-claim.md", mutated, canonical)


@pytest.mark.parametrize(
    "hidden_claim",
    (
        "<!-- dcc-mcp-core>=0.17.31 -->",
        "<span hidden>dcc-mcp-core>=0.17.31</span>",
        '<div style="display:none">dcc-mcp-core>=0.17.31</div>',
        '[unused-core]: badge.svg "dcc-mcp-core>=0.17.31"',
    ),
)
def test_rendered_markdown_scanner_ignores_non_rendered_core_claims(hidden_claim: str) -> None:
    canonical = _core_dependency()
    content = "Current requirement: %s\n%s\n" % (canonical, hidden_claim)

    _assert_surface_contract("hidden-claim.md", content, canonical)


def test_rendered_markdown_tokens_cannot_consume_the_next_line() -> None:
    canonical = _core_dependency()
    content = "![Core](badge.svg\nCurrent requirement: %s\n" % canonical

    _assert_surface_contract("bounded-token.md", content, canonical)


def test_escaped_html_comment_markup_remains_a_visible_core_claim() -> None:
    canonical = _core_dependency()
    content = "Current requirement: %s\n&lt;!-- dcc-mcp-core&gt;=0.17.31 --&gt;\n" % canonical

    with pytest.raises(AssertionError):
        _assert_surface_contract("escaped-comment.md", content, canonical)


def test_duplicate_reference_definitions_cannot_mask_the_first_visible_title() -> None:
    canonical = _core_dependency()
    content = (
        "Current requirement: %s\n"
        "![Core][core-badge]\n"
        '[core-badge]: badge.svg "dcc-mcp-core>=0.17.31"\n'
        '[core-badge]: badge.svg "harmless title"\n'
    ) % canonical

    with pytest.raises(AssertionError):
        _assert_surface_contract("duplicate-reference.md", content, canonical)


def test_single_segment_pep440_core_version_claim_is_rejected() -> None:
    canonical = _core_dependency()
    content = "Current requirement: %s\ndcc-mcp-core version 1\n" % canonical

    with pytest.raises(AssertionError):
        _assert_surface_contract("single-segment-version.md", content, canonical)


def test_readme_core_badge_uses_the_canonical_complete_upper_bound() -> None:
    content = unquote((ROOT / "README.md").read_text(encoding="utf-8"))

    assert "dcc--mcp--core->=0.19.45,<1.0.0-blue" in content
    assert "dcc--mcp--core->=0.19.45,<1.0-blue" not in content


def test_installer_core_dependency_contract_matches_package_metadata() -> None:
    from packaging.requirements import Requirement

    from dcc_mcp_maya import install

    assert install.CORE_VERSION_REQUIREMENT == _core_dependency()
    assert install._core_version_specifier() == Requirement(_core_dependency()).specifier
