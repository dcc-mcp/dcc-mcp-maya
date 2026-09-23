"""Runtime version provenance + startup consistency self-check.

Why this module exists
----------------------
Inside one Maya host the adapter version can be read from several places
and they do **not** always agree:

* ``importlib.metadata.version("dcc-mcp-maya")`` — the *installed
  distribution* metadata (``.dist-info`` / ``.egg-info``).  This is what
  ``pip`` believes is installed.
* ``dcc_mcp_maya.__version__`` — the module that is *actually imported*,
  i.e. the code that is actually running.
* the startup log line and the MCP ``initialize`` response — both derive
  from :data:`dcc_mcp_maya.__version__` (``server.DEFAULT_SERVER_VERSION``),
  which is also the value ``dcc-mcp-cli`` reports for the instance.

When a stale distribution (a wheel or editable install that was never
upgraded) sits next to a newer module on ``sys.path`` the first two answers
diverge — the reported case had metadata saying ``0.9.14`` while the running
module said ``0.9.16``.  Bug reports then describe an environment nobody can
reproduce, and compatibility matrices get read off the wrong number.

Policy implemented here
-----------------------
1. **Single source at packaging time.**  ``pyproject.toml`` carries
   ``project.version``; release-please bumps it *and*
   ``src/dcc_mcp_maya/__version__.py`` *and* every other file marked with
   ``x-release-please-version`` in the same release commit.  The wheel
   metadata is generated from ``project.version``, so a correct build has
   exactly one version.  ``tests/test_version_single_source.py`` fails CI
   when those files ever drift apart.
2. **The running module wins at runtime.**  ``dcc_mcp_maya.__version__`` is
   the code that executes, so it is what the server advertises in the MCP
   ``initialize`` response and what a bug report should quote.
3. **Drift is loud, never fatal.**  :func:`run_version_self_check` runs once
   during :meth:`dcc_mcp_maya.server.MayaMcpServer.start`, logs both answers
   with their paths, and emits a ``warning`` when they disagree.  It never
   raises — a version mismatch must not stop an artist from working.

The same comparison is applied to ``dcc-mcp-core``: its startup log line
(``dcc_mcp_core.__version__``) and its distribution metadata can drift the
same way, which is why "read the version off the log" was unreliable.

Python 3.7 support (Maya 2022)
------------------------------
:mod:`importlib.metadata` is 3.8+ and the ``importlib_metadata`` backport is
not a declared dependency (adding one for a diagnostics-only feature would
make every Maya 2022 install depend on a network-resolved wheel).  When
neither is importable, :func:`distribution_version` falls back to a pure
stdlib scan of ``sys.path`` for ``<package>-*.dist-info/METADATA`` and reads
the ``Version:`` field.  That keeps the drift check working on the py3.7
hosts where it matters most — those are the ones that still carry stale
installs from several releases ago.

Opt out with ``DCC_MCP_MAYA_VERSION_CHECK=0``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import io
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Import local modules
from dcc_mcp_maya import _env

logger = logging.getLogger(__name__)

#: Distribution name of this adapter (as ``pip`` knows it).
ADAPTER_PACKAGE = "dcc-mcp-maya"
#: Distribution name of the shared core library.
CORE_PACKAGE = "dcc-mcp-core"

#: Both answers exist and agree.
STATUS_CONSISTENT = "consistent"
#: Both answers exist but disagree — stale install or stale module on ``sys.path``.
STATUS_MISMATCH = "mismatch"
#: No installed-distribution metadata for the package (source checkout, vendored module zip).
STATUS_NOT_INSTALLED = "not-installed"
#: Not enough information to answer (no metadata API, import failure, no ``__version__``).
STATUS_UNKNOWN = "unknown"


def _metadata_module() -> Optional[Any]:
    """Return an ``importlib.metadata``-compatible module, or ``None``.

    ``importlib.metadata`` landed in Python 3.8; Maya 2022 still runs 3.7,
    where only the ``importlib_metadata`` backport provides the same API.
    """
    try:
        from importlib import metadata as importlib_metadata  # noqa: PLC0415
    except ImportError:  # pragma: no cover - Python 3.7 only
        try:
            import importlib_metadata  # type: ignore[no-redef]  # noqa: PLC0415
        except ImportError:
            return None
    return importlib_metadata


def _normalize_version(raw: Any) -> str:
    """Normalise *raw* so ``0.9.2`` and ``0.9.02`` compare equal.

    Falls back to a lower-cased string when :mod:`packaging` is unavailable
    or the value is not PEP 440 (``"unknown"``, ``"0.9.16+local"`` …).
    """
    text = "" if raw is None else str(raw).strip()
    if not text:
        return ""
    try:
        from packaging.version import Version  # noqa: PLC0415

        return str(Version(text))
    except Exception:  # noqa: BLE001 - InvalidVersion / ImportError / TypeError
        return text.lower()


def _metadata_field(metadata_text: str, field: str) -> Optional[str]:
    """Return the first ``Field: value`` line matching *field* (case-insensitive)."""
    prefix = field.lower() + ":"
    for line in metadata_text.splitlines():
        if line.lower().startswith(prefix):
            value = line[len(prefix) :].strip()
            if value:
                return value
    return None


def _scan_distribution_dirs(package: str) -> List[Tuple[str, str]]:
    """Find ``<package>-*.dist-info`` / ``.egg-info`` directories on ``sys.path``.

    Pure-stdlib stand-in for :mod:`importlib.metadata`, used on Python 3.7
    (Maya 2022) where neither the stdlib module nor the
    ``importlib_metadata`` backport is guaranteed to exist.  Returns
    ``(metadata_file, distribution_dir)`` pairs in ``sys.path`` order.
    """
    normalised = package.replace("-", "_")
    prefixes = (normalised + "-", package + "-")
    suffixes = (".dist-info", ".egg-info")
    found: List[Tuple[str, str]] = []

    for entry in sys.path:
        if not entry:
            continue
        try:
            names = sorted(os.listdir(entry))
        except OSError:  # noqa: BLE001 - unreadable / missing sys.path entry
            continue
        for name in names:
            lowered = name.lower()
            if not lowered.endswith(suffixes):
                continue
            if not any(lowered.startswith(prefix) for prefix in prefixes):
                continue
            metadata_file = os.path.join(entry, name, "METADATA")
            if not os.path.isfile(metadata_file):
                metadata_file = os.path.join(entry, name, "PKG-INFO")
                if not os.path.isfile(metadata_file):
                    continue
            found.append((metadata_file, os.path.join(entry, name)))
    return found


def _version_from_metadata_file(metadata_file: str) -> Optional[str]:
    try:
        with io.open(metadata_file, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
    except OSError:  # noqa: BLE001
        return None
    return _metadata_field(content, "Version")


def distribution_version(package: str) -> Optional[str]:
    """Return the installed-distribution version of *package*.

    Resolution order:

    1. :mod:`importlib.metadata` (Python 3.8+) or the ``importlib_metadata``
       backport, when importable.
    2. A pure-stdlib scan of ``sys.path`` for ``<package>-*.dist-info``, so
       Python 3.7 / Maya 2022 hosts are still covered.

    Returns ``None`` when no distribution metadata can be found at all.
    """
    metadata = _metadata_module()
    if metadata is not None:
        try:
            return str(metadata.version(package))
        except Exception:  # noqa: BLE001 - PackageNotFoundError and friends
            pass
        # Fall through: a partially-installed distribution can raise even when
        # a .dist-info directory is present, and the scan can still read it.

    for metadata_file, _distribution_dir in _scan_distribution_dirs(package):
        version = _version_from_metadata_file(metadata_file)
        if version:
            return version
    return None


def distribution_location(package: str) -> Optional[str]:
    """Return where the installed distribution of *package* lives on disk.

    Used in log lines so an operator can delete the stale ``.dist-info``
    without guessing which site-packages is responsible.
    """
    metadata = _metadata_module()
    if metadata is not None:
        try:
            distribution = metadata.distribution(package)
        except Exception:  # noqa: BLE001
            distribution = None
        if distribution is not None:
            try:
                return str(distribution.locate_file(""))
            except Exception:  # noqa: BLE001
                try:
                    return str(distribution._path)  # noqa: SLF001 - older backports
                except Exception:  # noqa: BLE001
                    pass

    for _metadata_file, distribution_dir in _scan_distribution_dirs(package):
        return distribution_dir
    return None


def module_origin(module: Optional[Any]) -> Optional[str]:
    """Return ``module.__file__`` as a string (``None`` when unavailable)."""
    try:
        origin = getattr(module, "__file__", None)
    except Exception:  # noqa: BLE001
        return None
    return str(origin) if origin else None


@dataclass
class VersionReport:
    """Version provenance for one package.

    Attributes
    ----------
    package:
        Distribution name (``dcc-mcp-maya`` / ``dcc-mcp-core``).
    runtime_version:
        ``__version__`` of the imported module — the code actually running.
    distribution_version:
        Version recorded in the installed distribution metadata.
    status:
        One of :data:`STATUS_CONSISTENT`, :data:`STATUS_MISMATCH`,
        :data:`STATUS_NOT_INSTALLED`, :data:`STATUS_UNKNOWN`.
    module_path:
        ``__file__`` of the imported module.
    distribution_path:
        Location of the distribution metadata on disk.
    detail:
        Human-readable explanation, empty when the report is consistent.
    """

    package: str
    runtime_version: Optional[str]
    distribution_version: Optional[str]
    status: str
    module_path: Optional[str] = None
    distribution_path: Optional[str] = None
    detail: str = ""

    @property
    def consistent(self) -> bool:
        """``True`` only when both answers exist and agree."""
        return self.status == STATUS_CONSISTENT

    @property
    def authoritative_version(self) -> Optional[str]:
        """Version to quote in bug reports — the running module wins."""
        return self.runtime_version or self.distribution_version

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of this report."""
        return {
            "package": self.package,
            "status": self.status,
            "consistent": self.consistent,
            "runtime_version": self.runtime_version,
            "distribution_version": self.distribution_version,
            "authoritative_version": self.authoritative_version,
            "module_path": self.module_path,
            "distribution_path": self.distribution_path,
            "detail": self.detail,
        }


def build_report(
    package: str,
    module: Optional[Any] = None,
    runtime_version: Optional[str] = None,
) -> VersionReport:
    """Compare the imported module version with the distribution metadata.

    Parameters
    ----------
    package:
        Distribution name to query through ``importlib.metadata``.
    module:
        Imported module to read ``__version__`` / ``__file__`` from.
    runtime_version:
        Explicit runtime version; takes precedence over ``module.__version__``.
    """
    if runtime_version is None and module is not None:
        runtime_version = getattr(module, "__version__", None)
    runtime_version = None if runtime_version is None else str(runtime_version)

    module_path = module_origin(module)
    installed = distribution_version(package)
    installed_path = distribution_location(package) if installed else None

    if runtime_version is None:
        return VersionReport(
            package=package,
            runtime_version=None,
            distribution_version=installed,
            status=STATUS_UNKNOWN,
            module_path=module_path,
            distribution_path=installed_path,
            detail="{} does not expose __version__".format(package),
        )

    if installed is None:
        if _metadata_module() is None:
            detail = "cannot read installed distribution metadata (Python 3.7 without the importlib_metadata backport)"
            status = STATUS_UNKNOWN
        else:
            detail = "no installed distribution metadata found (source checkout or vendored module)"
            status = STATUS_NOT_INSTALLED
        return VersionReport(
            package=package,
            runtime_version=runtime_version,
            distribution_version=None,
            status=status,
            module_path=module_path,
            distribution_path=None,
            detail=detail,
        )

    if _normalize_version(runtime_version) == _normalize_version(installed):
        return VersionReport(
            package=package,
            runtime_version=runtime_version,
            distribution_version=installed,
            status=STATUS_CONSISTENT,
            module_path=module_path,
            distribution_path=installed_path,
        )

    return VersionReport(
        package=package,
        runtime_version=runtime_version,
        distribution_version=installed,
        status=STATUS_MISMATCH,
        module_path=module_path,
        distribution_path=installed_path,
        detail="installed distribution metadata reports {} but the imported module reports {}".format(
            installed, runtime_version
        ),
    )


def adapter_report() -> VersionReport:
    """Report the version provenance of this adapter."""
    import dcc_mcp_maya  # noqa: PLC0415 - lazy: keeps import cheap and cycle-free

    return build_report(ADAPTER_PACKAGE, module=dcc_mcp_maya)


def core_report() -> VersionReport:
    """Report the version provenance of ``dcc-mcp-core``."""
    try:
        import dcc_mcp_core  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return VersionReport(
            package=CORE_PACKAGE,
            runtime_version=None,
            distribution_version=distribution_version(CORE_PACKAGE),
            status=STATUS_UNKNOWN,
            detail="import dcc_mcp_core failed: {}".format(exc),
        )
    return build_report(CORE_PACKAGE, module=dcc_mcp_core)


def collect_version_reports(include_core: bool = True) -> Dict[str, VersionReport]:
    """Collect reports for the adapter (and core), never raising."""
    reports: Dict[str, VersionReport] = {}

    def _safe(key: str, factory: Any) -> None:
        try:
            reports[key] = factory()
        except Exception as exc:  # noqa: BLE001 - diagnostics must not break startup
            reports[key] = VersionReport(
                package=key,
                runtime_version=None,
                distribution_version=None,
                status=STATUS_UNKNOWN,
                detail="{} self-check failed: {}".format(key, exc),
            )

    _safe("adapter", adapter_report)
    if include_core:
        _safe("core", core_report)
    return reports


def version_report(include_core: bool = True) -> Dict[str, Any]:
    """Return a JSON-serialisable version provenance payload (no logging).

    Shape::

        {
          "adapter": {...VersionReport...},
          "core": {...VersionReport...},
          "consistent": bool,   # every report is STATUS_CONSISTENT
          "drift": bool,        # at least one report is STATUS_MISMATCH
        }

    ``consistent`` is intentionally strict: a report that could not be
    decided (``not-installed`` for a source checkout, ``unknown`` when no
    metadata can be read) makes it ``False``.  Consumers that only care
    about real drift — "two answers exist and disagree" — must read
    ``drift`` instead.
    """
    reports = collect_version_reports(include_core=include_core)
    payload: Dict[str, Any] = {name: report.to_dict() for name, report in reports.items()}
    payload["consistent"] = all(report.consistent for report in reports.values())
    payload["drift"] = any(report.status == STATUS_MISMATCH for report in reports.values())
    return payload


def log_report(report: VersionReport, target_logger: Optional[logging.Logger] = None) -> None:
    """Log one report: ``info`` when healthy, ``warning`` on drift."""
    log = target_logger if target_logger is not None else logger
    version = report.authoritative_version or "unknown"

    if report.status == STATUS_MISMATCH:
        log.warning(
            "[maya] %s version drift — %s. The running module (%s) is what executes; "
            "reinstall %s to clear the stale distribution (module: %s; distribution: %s)",
            report.package,
            report.detail,
            version,
            report.package,
            report.module_path or "unknown",
            report.distribution_path or "unknown",
        )
        return

    if report.status == STATUS_CONSISTENT:
        log.info(
            "[maya] %s %s (module: %s)",
            report.package,
            version,
            report.module_path or "unknown",
        )
        return

    log.debug(
        "[maya] %s %s — %s (module: %s; status: %s)",
        report.package,
        version,
        report.detail,
        report.module_path or "unknown",
        report.status,
    )


def run_version_self_check(
    target_logger: Optional[logging.Logger] = None,
    include_core: bool = True,
) -> Dict[str, Any]:
    """Run the startup version self-check: log both answers, warn on drift.

    Never raises.  Returns the same payload as :func:`version_report` so
    callers (tests, diagnostics endpoints, gateway metadata) can reuse it.
    """
    reports = collect_version_reports(include_core=include_core)
    for report in reports.values():
        log_report(report, target_logger)
    payload: Dict[str, Any] = {name: report.to_dict() for name, report in reports.items()}
    payload["consistent"] = all(report.consistent for report in reports.values())
    payload["drift"] = any(report.status == STATUS_MISMATCH for report in reports.values())
    return payload


def version_self_check_enabled(flag: Optional[bool] = None) -> bool:
    """Return whether the startup self-check should run.

    Thin wrapper around :func:`dcc_mcp_maya._env.resolve_version_check_enabled`
    so callers do not need to import the env module directly.
    """
    return _env.resolve_version_check_enabled(flag)
