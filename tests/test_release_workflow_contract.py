"""Pin the release workflow's test gate to the same contract as ``ci.yml``.

Two consecutive releases (v0.9.27, v0.9.28) failed in the ``build`` job: it
ran pytest without the job-persistence env that ``ci.yml`` declares, so the
test session took the machine-wide exclusive SQLite lease. The second
in-process ``MayaMcpServer`` start then failed with "job persistence
unavailable (ownership)", ``publish``/``attach-release-assets`` were skipped,
and both releases shipped without a wheel or an sdist.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# Env that keeps a pytest run from taking the machine-wide job-storage lease.
JOB_STORAGE_ENV = {
    "DCC_MCP_DISABLE_JOB_PERSISTENCE": "1",
    "DCC_MCP_MAYA_JOB_STORAGE": "",
}

# Interpreters declared by the wheel classifiers; the release gate must stay
# inside them instead of running on an undeclared interpreter.
SUPPORTED_PYTHON = {"3.8", "3.9", "3.10", "3.11", "3.12"}

# Test directories ci.yml skips; the release gate must select the same tests.
IGNORED_TEST_DIRS = ("tests/e2e", "tests/e2e_standalone")


def _load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ci():
    return _load("ci.yml")


@pytest.fixture(scope="module")
def release():
    return _load("release.yml")


def _runs(steps):
    """Join shell scripts, unwrapping ``\\`` line continuations."""
    scripts = [step.get("run", "") for step in steps if isinstance(step.get("run", ""), str)]
    joined = " ".join(script.replace("\\\n", " ") for script in scripts)
    return " ".join(joined.split())


def test_ci_declares_the_job_persistence_contract(ci):
    """ci.yml is the source of truth for the hermetic test environment."""
    env = ci["jobs"]["test"].get("env") or {}
    for key, value in JOB_STORAGE_ENV.items():
        assert key in env, "ci.yml test job must declare %s" % key
        assert str(env[key]) == value


def test_release_build_job_disables_job_persistence(release):
    """The release test gate must run the same hermetic contract as ci.yml."""
    env = release["jobs"]["build"].get("env") or {}
    for key, value in JOB_STORAGE_ENV.items():
        assert key in env, "release build job must declare %s" % key
        assert str(env[key]) == value


def test_release_build_job_selects_the_same_tests_as_ci(release):
    """Release must not collect the e2e trees ci.yml ignores."""
    commands = _runs(release["jobs"]["build"]["steps"])
    assert "pytest" in commands, "release build job must run pytest"
    for directory in IGNORED_TEST_DIRS:
        assert "--ignore=%s" % directory in commands, "release pytest must ignore %s" % directory


def _setup_python_version(job):
    for step in job["steps"]:
        if str(step.get("uses", "")).startswith("actions/setup-python"):
            return str(step.get("with", {}).get("python-version", ""))
    return ""


@pytest.mark.parametrize("job_name", ["build", "build-mod"])
def test_release_jobs_use_a_declared_python_version(release, job_name):
    """Building on an undeclared interpreter silently widens the support matrix."""
    version = _setup_python_version(release["jobs"][job_name])
    assert version in SUPPORTED_PYTHON, "release %s job runs on undeclared Python %r" % (job_name, version)


def test_release_verifies_dist_artifacts_before_publishing(release):
    """A release must fail loudly instead of skipping PyPI with mod ZIPs only."""
    steps = release["jobs"]["build"]["steps"]
    names = [str(step.get("name", "")).lower() for step in steps]
    assert any("verify" in name and "dist" in name for name in names), (
        "release build job must verify dist/ before uploading artifacts"
    )
    verifier = _runs([step for step in steps if "verify" in str(step.get("name", "")).lower()])
    assert "*.whl" in verifier and "*.tar.gz" in verifier


def test_release_has_a_post_attach_asset_verification_job(release):
    """Post-release check catches "release is green but nothing was published"."""
    job = release["jobs"].get("verify-release-assets")
    assert job, "release.yml must define a verify-release-assets job"
    assert "attach-release-assets" in job["needs"]
    # The step shells out to ``grep -E``, so asset patterns carry escapes.
    commands = _runs(job["steps"]).replace("\\", "")
    assert "gh release view" in commands
    assert ".whl" in commands and ".tar.gz" in commands


@pytest.mark.parametrize("job_name", ["build", "build-mod"])
def test_release_jobs_build_the_requested_tag(release, job_name):
    """A manual backfill must build the tagged tree, not whatever main is.

    Without a pinned ``ref``, ``workflow_dispatch`` checks out the dispatch
    branch, so a backfill of v0.9.28 could build 0.9.29 artifacts, push them
    to PyPI (uploads are immutable) and attach them to the v0.9.28 release.
    """
    checkouts = [
        step for step in release["jobs"][job_name]["steps"] if str(step.get("uses", "")).startswith("actions/checkout")
    ]
    assert checkouts, "release %s job must check out the repository" % job_name
    ref = str(checkouts[0].get("with", {}).get("ref", ""))
    assert "inputs.tag_name" in ref, "release %s job must pin ref for backfills" % job_name
    assert "github.sha" in ref, "release %s job must keep the triggering SHA otherwise" % job_name


def test_release_build_job_checks_dist_matches_the_tag(release):
    """Artifacts must belong to the tag publish is about to target."""
    steps = release["jobs"]["build"]["steps"]
    check = [
        step
        for step in steps
        if "tag" in str(step.get("name", "")).lower() and "verify" in str(step.get("name", "")).lower()
    ]
    assert check, "release build job must verify the dist version against the tag"
    env = check[0].get("env") or {}
    assert "needs.release-please.outputs.version" in str(env.get("RELEASE_VERSION", ""))
    assert "inputs.tag_name" in str(env.get("TAG_NAME", ""))
    script = _runs(check)
    # A backfill builds the requested tag, so the version source must follow
    # the same precedence as the checkout ``ref``.
    assert "EVENT_NAME" in env and "workflow_dispatch" in script
    # The version must be anchored at a filename boundary: a bare prefix lets
    # "0.9.2" accept "dcc_mcp_maya-0.9.28-py3-none-any.whl".
    assert 'dcc_mcp_maya-%s-" % version' in script and 'dcc_mcp_maya-%s." % version' in script
