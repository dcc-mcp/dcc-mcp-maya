"""Registration phases for MayaMcpServer builtin actions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence


@dataclass
class RegistrationContext:
    """Input shared by every registration phase."""

    server: Any
    extra_skill_paths: Optional[List[str]] = None
    include_bundled: bool = True
    minimal: Optional[bool] = None
    strict_scan: Optional[bool] = None


@dataclass
class PhaseOutcome:
    """Result for one registration phase."""

    name: str
    success: bool
    elapsed_secs: float
    error: Optional[str] = None


@dataclass
class RegistrationReport:
    """Summary emitted after builtin-action registration completes."""

    outcomes: List[PhaseOutcome] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(outcome.success for outcome in self.outcomes)

    @property
    def elapsed_secs(self) -> float:
        return sum(outcome.elapsed_secs for outcome in self.outcomes)


class RegistrationPhase:
    """Base class for one side-effect in Maya builtin registration."""

    name = "registration"
    fatal_exceptions = ()

    def run(self, context: RegistrationContext) -> None:
        raise NotImplementedError


class CoreBuiltinActionsPhase(RegistrationPhase):
    name = "core_builtin_actions"

    def run(self, context: RegistrationContext) -> None:
        context.server._register_core_builtin_actions(context)  # noqa: SLF001


class MetadataDrivenToolsPhase(RegistrationPhase):
    """Expose ``recipes__*`` / ``skill_refs__*`` via core metadata registration.

    Replaces the previous ``RecipesToolsPhase`` + ``SkillReferenceDocsPhase``
    pair (issue PIP-179).  Core 0.17.38+ already registers the built-in
    ``recipes__*`` / ``qt_ui_inspector__*`` stubs during ``DccServerBase.__init__``;
    this phase re-registers them with the actual scanned skill set so
    ``metadata.dcc-mcp.recipes`` and peer reference docs are visible.

    Uses :func:`dcc_mcp_core.metadata_registration.register_metadata_driven_tools`.
    """

    name = "metadata_driven_tools"

    def run(self, context: RegistrationContext) -> None:
        context.server._register_metadata_driven_tools(context)  # noqa: SLF001


class StrictSkillScanPhase(RegistrationPhase):
    name = "strict_skill_scan"
    fatal_exceptions = (ValueError,)

    def run(self, context: RegistrationContext) -> None:
        context.server._run_strict_skill_scan_if_enabled(  # noqa: SLF001
            context.strict_scan,
            context.extra_skill_paths,
            context.include_bundled,
        )


class CapabilityManifestPhase(RegistrationPhase):
    name = "capability_manifest"

    def run(self, context: RegistrationContext) -> None:
        context.server._register_capability_manifest_tool()  # noqa: SLF001


class ProjectToolsPhase(RegistrationPhase):
    name = "project_tools"

    def run(self, context: RegistrationContext) -> None:
        context.server._attach_project_tools()  # noqa: SLF001


class ResourcesPhase(RegistrationPhase):
    name = "resources"

    def run(self, context: RegistrationContext) -> None:
        context.server._attach_resources()  # noqa: SLF001


def default_registration_phases() -> Sequence[RegistrationPhase]:
    return (
        CoreBuiltinActionsPhase(),
        MetadataDrivenToolsPhase(),
        StrictSkillScanPhase(),
        CapabilityManifestPhase(),
        ProjectToolsPhase(),
        ResourcesPhase(),
    )


def run_registration_phases(phases: Sequence[RegistrationPhase], context: RegistrationContext) -> RegistrationReport:
    report = RegistrationReport()
    for phase in phases:
        started = time.monotonic()
        try:
            phase.run(context)
        except phase.fatal_exceptions as exc:
            report.outcomes.append(
                PhaseOutcome(
                    name=phase.name,
                    success=False,
                    elapsed_secs=time.monotonic() - started,
                    error=str(exc),
                )
            )
            raise
        except Exception as exc:  # noqa: BLE001 - phase loop localizes optional integration failures
            report.outcomes.append(
                PhaseOutcome(
                    name=phase.name,
                    success=False,
                    elapsed_secs=time.monotonic() - started,
                    error=str(exc),
                )
            )
        else:
            report.outcomes.append(
                PhaseOutcome(
                    name=phase.name,
                    success=True,
                    elapsed_secs=time.monotonic() - started,
                )
            )
    return report
