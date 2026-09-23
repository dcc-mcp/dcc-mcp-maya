"""Keep every packaging / docs version claim on one source of truth.

``dcc-mcp-maya`` ships its version through release-please, which bumps
``pyproject.toml`` (``project.version``) and every file carrying the
``x-release-please-version`` marker in the same release commit.  A wheel's
``.dist-info`` metadata is generated from ``project.version`` while the
runtime reports ``dcc_mcp_maya.__version__``, so a divergence between those
two files is exactly the "metadata says 0.9.14, the module says 0.9.16"
failure from the field report.

These tests are file-based (not import-based) so they gate the repository
state in CI regardless of which adapter happens to be installed in the
interpreter running pytest.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import re
from pathlib import Path

# Import third-party modules
import pytest

try:
    # Import built-in modules
    import tomllib
except ImportError:  # pragma: no cover - Python 3.7-3.10
    # Import third-party modules
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
#: release-please keeps the released version here; it is the base for every
#: other claim and what ``.github/workflows/version-consistency.yml`` treats as
#: the source of truth (that job only runs when one of these files changes).
RELEASE_MANIFEST = ROOT / ".release-please-manifest.json"
VERSION_MODULE = ROOT / "src" / "dcc_mcp_maya" / "__version__.py"
RELEASE_PLEASE_CONFIG = ROOT / "release-please-config.json"
SERVER_MODULE = ROOT / "src" / "dcc_mcp_maya" / "server.py"

MARKER = "x-release-please-version"
VERSION_LITERAL = re.compile(r'^__version__\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE)
VERSION_TOKEN = re.compile(r"\d+\.\d+(?:\.\d+)?(?:[A-Za-z0-9.+-]*)?")


def _pyproject_version() -> str:
    return str(tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"])


def _module_version() -> str:
    match = VERSION_LITERAL.search(VERSION_MODULE.read_text(encoding="utf-8"))
    assert match is not None, "{} must declare __version__".format(VERSION_MODULE)
    return match.group("version")


def _release_please_files() -> list[Path]:
    """Files release-please rewrites on every release (the managed set)."""
    config = json.loads(RELEASE_PLEASE_CONFIG.read_text(encoding="utf-8"))
    return sorted(
        ROOT / entry["path"] for entry in config["packages"]["."]["extra-files"] if (ROOT / entry["path"]).is_file()
    )


def test_pyproject_and_module_version_agree():
    assert _pyproject_version() == _module_version()


def test_release_manifest_agrees_with_pyproject():
    """``.release-please-manifest.json`` is the base of the version chain."""
    manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["."] == _pyproject_version()


def test_version_module_carries_the_release_please_marker():
    text = VERSION_MODULE.read_text(encoding="utf-8")
    assert MARKER in text, "release-please must bump {} alongside pyproject.toml".format(VERSION_MODULE)


def test_release_please_manages_the_version_module_and_pyproject():
    config = json.loads(RELEASE_PLEASE_CONFIG.read_text(encoding="utf-8"))
    extra_files = config["packages"]["."]["extra-files"]
    paths = {entry["path"].replace("\\", "/") for entry in extra_files}

    assert "src/dcc_mcp_maya/__version__.py" in paths
    toml_entry = next(entry for entry in extra_files if entry["path"] == "pyproject.toml")
    assert toml_entry["jsonpath"] == "$.project.version"


@pytest.mark.parametrize("path", _release_please_files(), ids=lambda p: str(p.relative_to(ROOT)).replace("\\", "/"))
def test_every_released_version_claim_matches(path: Path):
    """Each marker line in a release-please-managed file quotes the release."""
    relative = str(path.relative_to(ROOT)).replace("\\", "/")
    expected = _pyproject_version()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if MARKER not in line:
            continue
        match = VERSION_TOKEN.search(line)
        assert match is not None, "{}:{} carries the marker but no version".format(relative, number)
        assert match.group(0) == expected, "{}:{} claims {}, expected {}".format(
            relative,
            number,
            match.group(0),
            expected,
        )


def test_advertised_server_version_comes_from_the_single_source():
    """The MCP ``initialize`` version must not be a hand-copied literal."""
    text = SERVER_MODULE.read_text(encoding="utf-8")
    assert "from dcc_mcp_maya.__version__ import __version__" in text
    assert re.search(r"^DEFAULT_SERVER_VERSION = __version__$", text, re.MULTILINE) is not None


def test_managed_file_set_covers_the_known_surfaces():
    """Guard against the release-please file list silently shrinking."""
    relative = {str(path.relative_to(ROOT)).replace("\\", "/") for path in _release_please_files()}
    assert "src/dcc_mcp_maya/__version__.py" in relative
    assert "AGENTS.md" in relative
    assert "llms.txt" in relative
