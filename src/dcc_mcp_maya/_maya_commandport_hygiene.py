"""Maya commandPort hygiene — not MCP transport (issues #148, #217).

We do **not** open commandPort for MCP or sidecar (those use HTTP and
``qtserver://``). This module only defuses Maya's **existing** listeners
(default ``:50007``, third-party ports) so stray probes do not block the
UI thread or flood the Script Editor.

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

* :func:`close_default_commandport` — closes Maya's default MEL commandPort
  on ``127.0.0.1:50007`` so HTTP probes cannot trigger a security dialog.
* :func:`configure_commandport_hygiene` — calls
  :func:`close_default_commandport` then :func:`suppress_security_warnings`
  (preferred plug-in entry point).
* :func:`suppress_security_warnings` — re-opens every currently-open
  commandPort with ``-securityWarning false``, **preserving each port's
  ``sourceType``** (``python`` vs ``mel``).  Forcing every listener to
  MEL turned Python smoke tests such as ``1+1;`` into Script Editor
  syntax-error spam when another tool still dialed a Python commandPort.
  Idempotent; never raises; never opens new ports.

Set ``DCC_MCP_MAYA_CLOSE_DEFAULT_COMMANDPORT=0`` to keep the default port open.
Set ``DCC_MCP_MAYA_DISABLE_COMMANDPORT_WARNING=0`` to opt out of warning suppression.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

ENV_DISABLE_WARNING = "DCC_MCP_MAYA_DISABLE_COMMANDPORT_WARNING"
ENV_CLOSE_DEFAULT = "DCC_MCP_MAYA_CLOSE_DEFAULT_COMMANDPORT"
_DEFAULT_COMMANDPORT_NAMES = (":50007", "commandportDefault")


def _is_disabled_by_env() -> bool:
    """Return True when the user opted out via env var (``=0``)."""
    return os.environ.get(ENV_DISABLE_WARNING, "1").strip() == "0"


def _close_default_enabled() -> bool:
    """Return True unless the user opted out of closing the default port."""
    return os.environ.get(ENV_CLOSE_DEFAULT, "1").strip() != "0"


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


def _port_source_type(cmds: object, port: str) -> str:
    """Return the ``sourceType`` of an open commandPort (default ``mel``)."""
    try:
        raw = cmds.commandPort(name=port, query=True, sourceType=True)  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001
        logger.debug("commandPort sourceType query failed for %s: %s", port, exc)
        return "mel"
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in ("python", "mel"):
            return lowered
    return "mel"


def configure_commandport_hygiene() -> None:
    """Close the default MEL listener, then suppress security warnings.

    Plug-in startup should call this once on the Maya main thread instead
    of invoking the helpers separately.
    """
    close_default_commandport()
    suppress_security_warnings()


def close_default_commandport() -> int:
    """Close Maya's default MEL commandPort if it is open.

    The default listener is named both ``:50007`` and ``commandportDefault``
    across Maya versions.  Closing it is safer than suppressing its security
    warning because dcc-mcp-maya never uses the legacy MEL transport.
    """
    if not _close_default_enabled():
        logger.debug("%s=0 — leaving default commandPort open", ENV_CLOSE_DEFAULT)
        return 0
    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return 0

    closed = 0
    for name in _DEFAULT_COMMANDPORT_NAMES:
        try:
            is_open = bool(cmds.commandPort(name, query=True, sourceType="mel"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("default commandPort query failed for %s: %s", name, exc)
            continue
        if not is_open:
            continue
        try:
            cmds.commandPort(name=name, close=True)
            closed += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("default commandPort close failed for %s: %s", name, exc)
    if closed:
        logger.info("Closed Maya default commandPort (%d alias(es)) — see issue #217", closed)
    return closed


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
            # not expose a runtime mutator for this attribute.  Preserve
            # the original sourceType — re-opening as MEL breaks any
            # Python listener still used by legacy MCP bridges.
            source_type = _port_source_type(cmds, port)
            cmds.commandPort(name=port, close=True)
            cmds.commandPort(
                name=port,
                securityWarning=False,
                sourceType=source_type,
            )
            fixed += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not disable security warning on %s: %s", port, exc)
    if fixed:
        logger.info(
            "Disabled commandPort security warning on %d port(s) — see issue #148",
            fixed,
        )
    return fixed
