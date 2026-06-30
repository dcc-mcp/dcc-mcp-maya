"""Registration phases for MayaMcpServer builtin actions.

Uses the shared phase framework from :mod:`dcc_mcp_core._registration`.
"""

from __future__ import annotations

from typing import Sequence

from dcc_mcp_core._registration import (
    CapabilityManifestPhase,
    CoreBuiltinActionsPhase,
    MetadataDrivenToolsPhase,
    ProjectToolsPhase,
    RegistrationPhase,
    ResourcesPhase,
    StrictSkillScanPhase,
    get_standard_phases,
)


def default_registration_phases() -> Sequence[RegistrationPhase]:
    """Return the ordered list of phases used by Maya."""
    # Use the core standard phases to ensure Maya gets all the unified
    # integrations (introspect, feedback, readiness, etc).
    return get_standard_phases()
