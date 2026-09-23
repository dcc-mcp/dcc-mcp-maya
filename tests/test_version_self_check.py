"""Tests for ``dcc_mcp_maya._version_check`` — runtime version provenance.

The reported bug this guards: inside one Maya host
``importlib.metadata.version("dcc-mcp-maya")`` answered ``0.9.14`` while
``dcc_mcp_maya.__version__`` answered ``0.9.16``.  Every way of asking for
the version must agree, and when they cannot, the drift must be logged
instead of silently accepted.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya import _env, _version_check


def _module(version, path="<memory>"):
    return SimpleNamespace(__version__=version, __file__=path)


def _raise_not_found(*_args, **_kwargs):
    """Stand-in for ``importlib.metadata`` raising ``PackageNotFoundError``."""
    raise RuntimeError("no such distribution")


class TestBuildReport:
    def test_consistent_when_both_answers_agree(self):
        module = _module("0.9.30", "/site-packages/dcc_mcp_maya/__init__.py")
        with patch.object(_version_check, "distribution_version", return_value="0.9.30"):
            report = _version_check.build_report("dcc-mcp-maya", module=module)

        assert report.status == _version_check.STATUS_CONSISTENT
        assert report.consistent is True
        assert report.runtime_version == "0.9.30"
        assert report.distribution_version == "0.9.30"
        assert report.detail == ""

    def test_pep440_normalisation_treats_equal_versions_as_consistent(self):
        with patch.object(_version_check, "distribution_version", return_value="0.9.2"):
            report = _version_check.build_report("dcc-mcp-maya", module=_module("0.9.02"))

        assert report.status == _version_check.STATUS_CONSISTENT

    def test_mismatch_reports_both_answers(self):
        module = _module("0.9.16", "/modules/dcc_mcp_maya/__init__.py")
        with patch.object(_version_check, "distribution_version", return_value="0.9.14"):
            report = _version_check.build_report("dcc-mcp-maya", module=module)

        assert report.status == _version_check.STATUS_MISMATCH
        assert report.consistent is False
        # The running module is what executes, so it is what bug reports quote.
        assert report.authoritative_version == "0.9.16"
        assert "0.9.14" in report.detail and "0.9.16" in report.detail

    def test_no_distribution_metadata_is_not_a_mismatch(self):
        module = _module("0.9.30")
        with patch.object(_version_check, "distribution_version", return_value=None):
            report = _version_check.build_report("dcc-mcp-maya", module=module)

        # A source checkout has no .dist-info — that is normal, not drift.
        assert report.status == _version_check.STATUS_NOT_INSTALLED
        assert report.consistent is False
        assert report.authoritative_version == "0.9.30"

    def test_missing_metadata_api_degrades_to_unknown(self, tmp_path, monkeypatch):
        # Isolate sys.path as well: without it the scan fallback would still
        # find the real installed dist-info and report a (correct) mismatch
        # instead of "cannot decide".
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        with patch.object(_version_check, "_metadata_module", return_value=None):
            report = _version_check.build_report("dcc-mcp-maya", module=_module("0.9.30"))

        assert report.status == _version_check.STATUS_UNKNOWN
        assert "importlib_metadata" in report.detail

    def test_unknown_detail_names_both_conditions_not_the_py37_backport(self, tmp_path, monkeypatch):
        # "unknown" means two things at once: no metadata API *and* an empty
        # sys.path scan.  The old wording blamed "Python 3.7 without the
        # importlib_metadata backport" alone, which sent operators hunting for
        # a missing package on hosts where the real cause was a bad sys.path.
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        with patch.object(_version_check, "_metadata_module", return_value=None):
            report = _version_check.build_report("dcc-mcp-maya", module=_module("0.9.30"))

        assert report.status == _version_check.STATUS_UNKNOWN
        assert "importlib.metadata" in report.detail
        assert "importlib_metadata" in report.detail
        assert "sys.path" in report.detail
        assert "dcc-mcp-maya" in report.detail
        # "not-installed" is a different verdict: it means an API exists and
        # answered "no such distribution", so the two must not be confused.
        assert report.distribution_version is None

    def test_not_installed_detail_is_used_when_the_metadata_api_exists(self, monkeypatch):
        monkeypatch.setattr(sys, "path", [])
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: SimpleNamespace(version=_raise_not_found, distribution=_raise_not_found),
        )

        report = _version_check.build_report("dcc-mcp-maya", module=_module("0.9.30"))

        assert report.status == _version_check.STATUS_NOT_INSTALLED
        assert "sys.path" not in report.detail

    def test_module_without_dunder_version_is_unknown(self):
        with patch.object(_version_check, "distribution_version", return_value="0.9.30"):
            report = _version_check.build_report("dcc-mcp-maya", module=SimpleNamespace())

        assert report.status == _version_check.STATUS_UNKNOWN

    def test_explicit_runtime_version_wins_over_module(self):
        with patch.object(_version_check, "distribution_version", return_value="0.9.30"):
            report = _version_check.build_report(
                "dcc-mcp-maya",
                module=_module("0.9.1"),
                runtime_version="0.9.30",
            )

        assert report.status == _version_check.STATUS_CONSISTENT

    def test_report_is_json_serialisable(self):
        with patch.object(_version_check, "distribution_version", return_value="0.9.30"):
            report = _version_check.build_report(
                "dcc-mcp-maya",
                module=_module("0.9.30", "/x/__init__.py"),
            )
        payload = report.to_dict()

        assert payload["package"] == "dcc-mcp-maya"
        assert payload["status"] == _version_check.STATUS_CONSISTENT
        assert payload["module_path"] == "/x/__init__.py"
        assert set(payload) == {
            "package",
            "status",
            "consistent",
            "runtime_version",
            "distribution_version",
            "authoritative_version",
            "module_path",
            "distribution_path",
            "detail",
        }


class TestLogging:
    def test_drift_logs_a_warning_naming_both_versions(self, caplog):
        module = _module("0.9.16", "/modules/dcc_mcp_maya/__init__.py")
        with patch.object(_version_check, "distribution_version", return_value="0.9.14"):
            with patch.object(_version_check, "distribution_location", return_value="/site-packages"):
                report = _version_check.build_report("dcc-mcp-maya", module=module)

        with caplog.at_level(logging.WARNING):
            _version_check.log_report(report, logging.getLogger("drift-test"))

        warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
        assert warnings, "version drift must not be silent"
        message = warnings[0].getMessage()
        assert "0.9.14" in message and "0.9.16" in message
        assert "/modules/dcc_mcp_maya/__init__.py" in message
        assert "/site-packages" in message

    def test_healthy_report_logs_info_not_warning(self, caplog):
        report = _version_check.VersionReport(
            package="dcc-mcp-maya",
            runtime_version="0.9.30",
            distribution_version="0.9.30",
            status=_version_check.STATUS_CONSISTENT,
            module_path="/x/__init__.py",
        )

        with caplog.at_level(logging.DEBUG):
            _version_check.log_report(report, logging.getLogger("healthy-test"))

        assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
        assert any("0.9.30" in r.getMessage() for r in caplog.records)

    def test_not_installed_is_debug_only(self, caplog):
        report = _version_check.VersionReport(
            package="dcc-mcp-maya",
            runtime_version="0.9.30",
            distribution_version=None,
            status=_version_check.STATUS_NOT_INSTALLED,
            detail="no installed distribution metadata found",
        )

        with caplog.at_level(logging.DEBUG):
            _version_check.log_report(report, logging.getLogger("noinstall-test"))

        assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
        assert all(r.levelno == logging.DEBUG for r in caplog.records)


class TestCollectAndRun:
    def test_payload_shape(self):
        with patch.object(_version_check, "adapter_report") as adapter, patch.object(
            _version_check, "core_report"
        ) as core:
            adapter.return_value = _version_check.VersionReport(
                package="dcc-mcp-maya",
                runtime_version="0.9.30",
                distribution_version="0.9.30",
                status=_version_check.STATUS_CONSISTENT,
            )
            core.return_value = _version_check.VersionReport(
                package="dcc-mcp-core",
                runtime_version="0.19.45",
                distribution_version="0.19.45",
                status=_version_check.STATUS_CONSISTENT,
            )
            payload = _version_check.version_report()

        assert payload["consistent"] is True
        assert payload["adapter"]["package"] == "dcc-mcp-maya"
        assert payload["core"]["runtime_version"] == "0.19.45"

    def test_core_mismatch_makes_the_payload_inconsistent(self):
        with patch.object(_version_check, "adapter_report") as adapter, patch.object(
            _version_check, "core_report"
        ) as core:
            adapter.return_value = _version_check.VersionReport(
                package="dcc-mcp-maya",
                runtime_version="0.9.30",
                distribution_version="0.9.30",
                status=_version_check.STATUS_CONSISTENT,
            )
            core.return_value = _version_check.VersionReport(
                package="dcc-mcp-core",
                runtime_version="0.19.2",
                distribution_version="0.19.3",
                status=_version_check.STATUS_MISMATCH,
                detail="log line vs metadata disagree",
            )
            payload = _version_check.version_report()

        # Core drift is exactly the "log shows 0.19.2, metadata says 0.19.3" case.
        assert payload["consistent"] is False
        assert payload["core"]["status"] == _version_check.STATUS_MISMATCH

    def test_core_can_be_excluded(self):
        with patch.object(_version_check, "adapter_report") as adapter:
            adapter.return_value = _version_check.VersionReport(
                package="dcc-mcp-maya",
                runtime_version="0.9.30",
                distribution_version="0.9.30",
                status=_version_check.STATUS_CONSISTENT,
            )
            payload = _version_check.version_report(include_core=False)

        assert "core" not in payload

    def test_collect_never_raises_when_a_report_fails(self):
        with patch.object(_version_check, "adapter_report", side_effect=RuntimeError("boom")):
            reports = _version_check.collect_version_reports(include_core=False)

        assert reports["adapter"].status == _version_check.STATUS_UNKNOWN
        assert "boom" in reports["adapter"].detail

    def test_run_self_check_returns_payload_and_logs(self, caplog):
        with patch.object(_version_check, "adapter_report") as adapter, patch.object(
            _version_check, "core_report"
        ) as core:
            adapter.return_value = _version_check.VersionReport(
                package="dcc-mcp-maya",
                runtime_version="0.9.16",
                distribution_version="0.9.14",
                status=_version_check.STATUS_MISMATCH,
                detail="installed distribution metadata reports 0.9.14 but the imported module reports 0.9.16",
            )
            core.return_value = _version_check.VersionReport(
                package="dcc-mcp-core",
                runtime_version="0.19.45",
                distribution_version="0.19.45",
                status=_version_check.STATUS_CONSISTENT,
            )
            with caplog.at_level(logging.DEBUG):
                payload = _version_check.run_version_self_check(logging.getLogger("selfcheck-test"))

        assert payload["consistent"] is False
        assert any(record.levelno == logging.WARNING for record in caplog.records)


class TestDistributionScanFallback:
    """End-to-end drift coverage against a real ``.dist-info`` directory.

    Python 3.7 (Maya 2022) has no :mod:`importlib.metadata` and the
    ``importlib_metadata`` backport is not a declared dependency, so the
    pure-stdlib ``sys.path`` scan inside :func:`distribution_version` is what
    keeps the drift check alive on those hosts — the platform the reported
    Maya 2022 host runs on.  These tests build an actual stale distribution
    directory instead of stubbing the resolver.

    Note: :mod:`importlib.metadata` caches ``sys.path`` in a default-argument
    ``Context``, so a synthetic directory cannot be pointed at deterministically.
    The scan fallback is exercised here; the "metadata API wins when present"
    ordering is covered by :meth:`test_metadata_api_takes_priority`.
    """

    @staticmethod
    def _make_dist_info(root: Path, package: str, version: str) -> Path:
        dist_info = root / "{}-{}.dist-info".format(package, version)
        dist_info.mkdir(parents=True, exist_ok=True)
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: {}\nVersion: {}\n".format(package, version),
            encoding="utf-8",
        )
        return dist_info

    def test_stale_dist_info_is_detected_as_drift(self, tmp_path, monkeypatch):
        site = self._make_dist_info(tmp_path, "dcc-mcp-maya", "0.9.14")
        monkeypatch.setattr(sys, "path", [str(tmp_path)] + list(sys.path))
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        report = _version_check.build_report(
            "dcc-mcp-maya", module=_module("0.9.16", "/modules/dcc_mcp_maya/__init__.py")
        )

        assert report.distribution_version == "0.9.14"
        assert report.runtime_version == "0.9.16"
        assert report.status == _version_check.STATUS_MISMATCH
        assert report.authoritative_version == "0.9.16"
        assert str(site).lower() in (report.distribution_path or "").lower()

    def test_matching_dist_info_is_consistent(self, tmp_path, monkeypatch):
        self._make_dist_info(tmp_path, "dcc-mcp-maya", "0.9.30")
        monkeypatch.setattr(sys, "path", [str(tmp_path)] + list(sys.path))
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        report = _version_check.build_report("dcc-mcp-maya", module=_module("0.9.30"))

        assert report.status == _version_check.STATUS_CONSISTENT

    def test_egg_info_is_also_recognised(self, tmp_path, monkeypatch):
        egg_info = tmp_path / "dcc_mcp_maya-0.9.1.egg-info"
        egg_info.mkdir(parents=True)
        (egg_info / "PKG-INFO").write_text("Name: dcc-mcp-maya\nVersion: 0.9.1\n", encoding="utf-8")
        monkeypatch.setattr(sys, "path", [str(tmp_path)] + list(sys.path))
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.1"

    def test_single_file_egg_info_is_parsed(self, tmp_path, monkeypatch):
        # setuptools documents the ``.egg-info`` artifact as possibly being a
        # single file that *is* the PKG-INFO payload, with no directory around it.
        egg_info = tmp_path / "dcc_mcp_maya.egg-info"
        egg_info.write_text("Name: dcc-mcp-maya\nVersion: 0.9.7\n", encoding="utf-8")
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.7"
        # There is no directory to delete, so the artifact itself is the answer.
        assert _version_check.distribution_location("dcc-mcp-maya") == str(egg_info)

    def test_unversioned_egg_info_directory_is_recognised(self, tmp_path, monkeypatch):
        # Editable installs write an unversioned ``<package>.egg-info`` directory.
        egg_info = tmp_path / "dcc-mcp-maya.egg-info"
        egg_info.mkdir(parents=True)
        (egg_info / "PKG-INFO").write_text("Name: dcc-mcp-maya\nVersion: 0.9.8\n", encoding="utf-8")
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.8"

    def test_highest_pep440_version_wins_in_one_directory(self, tmp_path, monkeypatch):
        # Lexicographic ordering ranks "0.9.2" above "0.9.30" -- the opposite of
        # what an operator reading a drift warning needs.
        for version in ("0.9.2", "0.9.30", "0.9.16"):
            self._make_dist_info(tmp_path, "dcc-mcp-maya", version)
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.30"
        expected = str(tmp_path / "dcc-mcp-maya-0.9.30.dist-info")
        assert _version_check.distribution_location("dcc-mcp-maya") == expected

    def test_sys_path_order_still_beats_version_ordering(self, tmp_path, monkeypatch):
        # Version ordering applies *within* one sys.path entry only; the first
        # entry on sys.path is still the one Python would import.
        first = tmp_path / "first"
        second = tmp_path / "second"
        self._make_dist_info(first, "dcc-mcp-maya", "0.9.2")
        self._make_dist_info(second, "dcc-mcp-maya", "0.9.30")
        monkeypatch.setattr(sys, "path", [str(first), str(second)])
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.2"

    def test_metadata_api_answering_none_falls_through_to_the_scan(self, tmp_path, monkeypatch):
        # A malformed METADATA without a ``Version:`` field can make the API
        # answer empty; str() would have smuggled the literal "None" into the
        # report, so the scan has to get its turn instead.
        self._make_dist_info(tmp_path, "dcc-mcp-maya", "0.9.30")
        monkeypatch.setattr(sys, "path", [str(tmp_path)] + list(sys.path))
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: SimpleNamespace(version=lambda _name: None),
        )

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.30"

    def test_metadata_api_answering_empty_string_falls_through(self, tmp_path, monkeypatch):
        self._make_dist_info(tmp_path, "dcc-mcp-maya", "0.9.30")
        monkeypatch.setattr(sys, "path", [str(tmp_path)] + list(sys.path))
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: SimpleNamespace(version=lambda _name: ""),
        )

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.30"

    def test_empty_api_answer_without_dist_info_stays_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: SimpleNamespace(version=lambda _name: None),
        )

        assert _version_check.distribution_version("dcc-mcp-maya") is None
        # ...and the report therefore says "not installed", never "None".
        report = _version_check.build_report("dcc-mcp-maya", module=_module("0.9.30"))

        assert report.status == _version_check.STATUS_NOT_INSTALLED
        assert report.distribution_version is None
        assert "None" not in report.detail

    def test_scan_finds_nothing_without_metadata_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)

        assert _version_check.distribution_version("dcc-mcp-maya") is None
        assert _version_check.distribution_location("dcc-mcp-maya") is None

    def test_metadata_api_takes_priority_when_available(self, tmp_path, monkeypatch):
        """When the metadata API works it is consulted before the scan."""
        self._make_dist_info(tmp_path, "dcc-mcp-maya", "0.9.14")
        monkeypatch.setattr(sys, "path", [str(tmp_path)] + list(sys.path))
        monkeypatch.setattr(_version_check, "_metadata_module", lambda: SimpleNamespace(version=lambda _name: "0.9.99"))

        assert _version_check.distribution_version("dcc-mcp-maya") == "0.9.99"

    def test_drift_flag_is_independent_of_undecidable_reports(self):
        """``consistent`` is strict; ``drift`` means "two answers disagree"."""
        undecidable = _version_check.VersionReport(
            package="dcc-mcp-maya",
            runtime_version="0.9.30",
            distribution_version=None,
            status=_version_check.STATUS_NOT_INSTALLED,
        )
        drifted = _version_check.VersionReport(
            package="dcc-mcp-core",
            runtime_version="0.19.2",
            distribution_version="0.19.3",
            status=_version_check.STATUS_MISMATCH,
        )
        with patch.object(_version_check, "adapter_report", return_value=undecidable), patch.object(
            _version_check, "core_report", return_value=drifted
        ):
            payload = _version_check.version_report()

        assert payload["consistent"] is False
        assert payload["drift"] is True

        healthy = _version_check.VersionReport(
            package="dcc-mcp-core",
            runtime_version="0.19.3",
            distribution_version="0.19.3",
            status=_version_check.STATUS_CONSISTENT,
        )
        with patch.object(_version_check, "adapter_report", return_value=undecidable), patch.object(
            _version_check, "core_report", return_value=healthy
        ):
            payload = _version_check.version_report()

        # A source checkout is not consistent, but it is not drift either.
        assert payload["consistent"] is False
        assert payload["drift"] is False


class TestVersionSortKey:
    """PEP 440 ordering for the candidates found inside one directory."""

    def test_numeric_versions_beat_lexicographic_order(self):
        ordered = sorted(("0.9.2", "0.9.30"), key=_version_check._version_sort_key, reverse=True)

        assert ordered == ["0.9.30", "0.9.2"]

    def test_non_pep440_versions_sort_last_without_raising(self):
        ordered = sorted(
            ("not-a-version", "0.9.2", "0.9.30"),
            key=_version_check._version_sort_key,
            reverse=True,
        )

        assert ordered[0] == "0.9.30"
        assert ordered[-1] == "not-a-version"

    def test_empty_version_is_a_stable_key(self):
        assert _version_check._version_sort_key("") == _version_check._version_sort_key(None)


class TestDistributionLocation:
    """Both resolution paths must answer at ``.dist-info`` granularity.

    The docstring promises an operator can delete the stale artifact without
    guessing, so "somewhere under site-packages" is not an answer.
    """

    @staticmethod
    def _fake_metadata(dist_path=None, site_root=None):
        distribution = SimpleNamespace(_path=dist_path, locate_file=lambda _relative: site_root)
        return SimpleNamespace(distribution=lambda _name: distribution)

    def test_metadata_api_prefers_the_dist_info_directory(self, monkeypatch):
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: self._fake_metadata("/sp/dcc_mcp_maya-0.9.30.dist-info", "/sp"),
        )

        assert _version_check.distribution_location("dcc-mcp-maya") == "/sp/dcc_mcp_maya-0.9.30.dist-info"

    def test_falls_back_to_locate_file_without_dist_info_path(self, monkeypatch):
        # Backports that do not expose ``_path`` must still get an answer.
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: self._fake_metadata(None, "/site-packages"),
        )

        assert _version_check.distribution_location("dcc-mcp-maya") == "/site-packages"

    def test_empty_dist_info_path_falls_back_to_locate_file(self, monkeypatch):
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: self._fake_metadata("", "/site-packages"),
        )

        assert _version_check.distribution_location("dcc-mcp-maya") == "/site-packages"

    def test_returns_none_when_both_api_answers_are_unusable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "path", [str(tmp_path)])
        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: self._fake_metadata(None, None),
        )

        assert _version_check.distribution_location("dcc-mcp-maya") is None

    def test_both_paths_agree_on_granularity(self, tmp_path, monkeypatch):
        # The scan branch always answered with the ``.dist-info`` directory;
        # the API branch used to answer with its parent.  Neither is useful
        # while the two disagree, so pin them together.
        dist_info = tmp_path / "dcc-mcp-maya-0.9.30.dist-info"
        dist_info.mkdir()
        (dist_info / "METADATA").write_text("Name: dcc-mcp-maya\nVersion: 0.9.30\n", encoding="utf-8")
        monkeypatch.setattr(sys, "path", [str(tmp_path)])

        monkeypatch.setattr(
            _version_check,
            "_metadata_module",
            lambda: self._fake_metadata(str(dist_info), str(tmp_path)),
        )
        via_api = _version_check.distribution_location("dcc-mcp-maya")

        monkeypatch.setattr(_version_check, "_metadata_module", lambda: None)
        via_scan = _version_check.distribution_location("dcc-mcp-maya")

        assert via_api == via_scan == str(dist_info)


class TestEnvResolution:
    def test_enabled_by_default(self):
        env = os.environ.copy()
        env.pop(_env.ENV_VERSION_CHECK, None)
        with patch.dict(os.environ, env, clear=True):
            assert _env.resolve_version_check_enabled() is True

    def test_env_zero_disables(self):
        with patch.dict(os.environ, {_env.ENV_VERSION_CHECK: "0"}):
            assert _env.resolve_version_check_enabled() is False

    def test_explicit_flag_wins(self):
        with patch.dict(os.environ, {_env.ENV_VERSION_CHECK: "0"}):
            assert _env.resolve_version_check_enabled(True) is True
        with patch.dict(os.environ, {_env.ENV_VERSION_CHECK: "1"}):
            assert _env.resolve_version_check_enabled(False) is False


class TestServerWiring:
    """``MayaMcpServer`` must run the check on start, once, and never crash."""

    @pytest.fixture()
    def server(self):
        # Build the instance without running ``__init__`` (no Maya, no HTTP).
        from dcc_mcp_maya.server import MayaMcpServer

        instance = MayaMcpServer.__new__(MayaMcpServer)
        instance._dcc_name = "maya"
        instance._version_report = None
        instance._version_self_checked = False
        return instance

    def test_start_runs_the_check_exactly_once(self, server):
        with patch(
            "dcc_mcp_maya.server.run_version_self_check",
            return_value={"consistent": True},
        ) as run:
            server._run_version_self_check()
            server._run_version_self_check()

        assert run.call_count == 1
        assert server._version_report == {"consistent": True}

    def test_env_opt_out_skips_the_check(self, server):
        with patch.dict(os.environ, {_env.ENV_VERSION_CHECK: "0"}):
            with patch("dcc_mcp_maya.server.run_version_self_check") as run:
                server._run_version_self_check()

        assert run.call_count == 0

    def test_a_failing_check_never_breaks_startup(self, server):
        with patch("dcc_mcp_maya.server.run_version_self_check", side_effect=RuntimeError("boom")):
            server._run_version_self_check()  # must not raise

        assert server._version_report is None

    def test_version_report_degrades_to_empty_dict(self, server):
        # Resolve through the server module: several suites purge
        # ``dcc_mcp_maya*`` from ``sys.modules`` and re-import the package,
        # so a module reference captured at import time can go stale.
        with patch("dcc_mcp_maya.server._version_check.version_report", side_effect=RuntimeError("boom")):
            assert server.version_report() == {}
