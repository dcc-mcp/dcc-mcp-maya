"""commandPort security-warning suppression (issue #148).

Maya's legacy ``commandPort`` shows a modal "Allow / Deny / Allow All"
dialog the first time it receives a payload from an unfamiliar source.
That dialog blocks Maya's main thread, which in turn freezes every
in-process MCP tool call.  Misrouted MCP traffic (gateway probes,
clients that point at the commandPort port instead of ``/mcp``) used to
trigger this dialog repeatedly.

dcc-mcp-core 0.14.20 (PR #632) filters non-MCP listeners out of gateway
fan-out, but defence-in-depth on the Maya side is still useful for
sessions where the user (or a third-party plugin) explicitly opened a
commandPort for unrelated tooling.

This module exposes a single best-effort helper:

* :func:`suppress_security_warnings` — re-opens every currently-open
  commandPort with ``-securityWarning false``, so the modal dialog
  never appears.  Idempotent; never raises; never opens new ports.

Set ``DCC_MCP_MAYA_DISABLE_COMMANDPORT_WARNING=0`` to opt out.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

ENV_DISABLE_WARNING = "DCC_MCP_MAYA_DISABLE_COMMANDPORT_WARNING"


def _is_disabled_by_env() -> bool:
    """Return True when the user opted out via env var (``=0``)."""
    return os.environ.get(ENV_DISABLE_WARNING, "1").strip() == "0"


def _list_open_ports() -> List[str]:
    """Return the names of every currently-open commandPort.

    Maya's ``commandPort -q -name`` returns either ``None``, a single
    string, or a list of strings depending on Maya version.  This helper
    normalises the return value to ``List[str]`` and never raises.
    """
    try:
        import maya.mel as mel  # noqa: PLC0415
    except ImportError:
        return []

    try:
        raw = mel.eval("commandPort -q -name;")
    except Exception as exc:  # noqa: BLE001
        logger.debug("commandPort query failed: %s", exc)
        return []

    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw] if raw else []
    try:
        return [str(p) for p in raw if p]
    except TypeError:
        return []


def suppress_security_warnings() -> int:
    """Disable the commandPort security warning on every open port.

    Walks every port returned by ``commandPort -q -name`` and re-opens
    it with ``-securityWarning false`` so subsequent requests skip the
    modal dialog.  Pass-through when:

    * Maya is not importable (standalone build, ``mayapy`` test run).
    * No ports are open (the common case when the user has not enabled
      commandPort manually).
    * The user opted out via :data:`ENV_DISABLE_WARNING` ``=0``.

    Returns
    -------
    int
        The number of ports that were re-opened with the warning
        disabled.  ``0`` covers every no-op path above.
    """
    if _is_disabled_by_env():
        logger.debug("%s=0 — leaving commandPort security warnings on", ENV_DISABLE_WARNING)
        return 0

    ports = _list_open_ports()
    if not ports:
        return 0

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return 0

    fixed = 0
    for port in ports:
        try:
            # Closing then re-opening with -securityWarning false is the
            # only way to flip the flag on an existing port; Maya does
            # not expose a runtime mutator for this attribute.
            cmds.commandPort(name=port, close=True)
            cmds.commandPort(name=port, securityWarning=False, sourceType="mel")
            fixed += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not disable security warning on %s: %s", port, exc)
    if fixed:
        logger.info(
            "Disabled commandPort security warning on %d port(s) — see issue #148",
            fixed,
        )
    return fixed
