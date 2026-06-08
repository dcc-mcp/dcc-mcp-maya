"""Registration phases for MayaMcpServer builtin actions.

Shared base classes (RegistrationContext, RegistrationPhase,
PhaseOutcome, RegistrationReport) and the executor
(run_registration_phases) are imported from
:mod:`dcc_mcp_core._registration` (PIP-689, core v0.18.14+).

Adapters define their own phase subclasses here for host-specific
registration steps.
"""

from __future__ import annotations

from typing import Sequence

from dcc_mcp_core._registration import (
    PhaseOutcome,
    RegistrationContext,
    RegistrationPhase,
    RegistrationReport,
    run_registration_phases,
)


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
