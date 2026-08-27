"""Keep the supported dcc-mcp-core range consistent across release surfaces."""

import re
import unicodedata
from pathlib import Path
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
VERSION_CLAIM = re.compile(r"\d+(?:\.\d+)+")
MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
MARKDOWN_LINK = re.compile(r"\[(?P<label>[^\]]+)\]\([^)]+\)")
MARKDOWN_REFERENCE_LINK = re.compile(r"\[(?P<label>[^\]]+)\]\[[^\]]*\]")
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
)


def _core_dependency() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return next(dependency for dependency in project["dependencies"] if dependency.startswith("dcc-mcp-core"))


def _normalize_surface(content: str) -> str:
    decoded = MARKDOWN_IMAGE.sub("", content)
    decoded = unquote(decoded)
    decoded = MARKDOWN_LINK.sub(lambda match: match.group("label").strip("`"), decoded)
    decoded = MARKDOWN_REFERENCE_LINK.sub(lambda match: match.group("label").strip("`"), decoded)
    decoded = unicodedata.normalize("NFKC", decoded).translate(UNICODE_HYPHENS)
    decoded = decoded.replace("≥", ">=").replace("≤", "<=")
    return CORE_PACKAGE_SPELLING.sub("dcc-mcp-core", decoded)


def _unparsed_core_claims(content: str) -> list[str]:
    claims = []
    for line in content.splitlines():
        names = list(CORE_NAME.finditer(line))
        for index, name in enumerate(names):
            end = names[index + 1].start() if index + 1 < len(names) else len(line)
            segment = line[name.start() : end]
            is_symbol_reference = segment.startswith("dcc-mcp-core.")
            if (
                VERSION_CLAIM.search(segment)
                and not is_symbol_reference
                and CORE_DECLARATION.match(line, name.start()) is None
            ):
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
    ),
)
def test_surface_contract_rejects_duplicate_or_alternate_dependency_declarations(injected: str) -> None:
    canonical = _core_dependency()
    mutated = f"Current requirement: {canonical}\nContradictory declaration: {injected}\n"

    with pytest.raises(AssertionError):
        _assert_surface_contract("mutated-public-surface.md", mutated, canonical)


def test_readme_core_badge_uses_the_canonical_complete_upper_bound() -> None:
    content = unquote((ROOT / "README.md").read_text(encoding="utf-8"))

    assert "dcc--mcp--core->=0.19.45,<1.0.0-blue" in content
    assert "dcc--mcp--core->=0.19.45,<1.0-blue" not in content


def test_installer_core_dependency_contract_matches_package_metadata() -> None:
    from packaging.requirements import Requirement

    from dcc_mcp_maya import install

    assert install.CORE_VERSION_REQUIREMENT == _core_dependency()
    assert install.CORE_VERSION_SPECIFIER == Requirement(_core_dependency()).specifier
