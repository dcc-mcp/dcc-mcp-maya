"""Minimal-mode skill loading (issue #127).

Houses the ``MINIMAL_SKILLS`` / ``MINIMAL_DEACTIVATE_GROUPS`` constants
and the two loader entry points used by
:meth:`MayaMcpServer.register_builtin_actions`:

* :func:`load_all_discovered_skills` — legacy "load every discovered
  skill at startup" path.
* :func:`load_minimal_skills` — load just the listed skills and
  deactivate the per-skill ``__group__<name>`` stubs declared in
  :data:`MINIMAL_DEACTIVATE_GROUPS`.

The functions take a ``server`` (an :class:`McpHttpServer` instance) so
they can be tested with a mock without owning a :class:`MayaMcpServer`.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

#: Skills loaded at startup when ``minimal=True`` (the default).
MINIMAL_SKILLS: List[str] = ["maya-scripting", "maya-scene"]

#: Per-skill ``{skill_name: [group_name, ...]}`` map of tool groups to
#: deactivate after :meth:`load_skill`.  Deactivated groups appear in
#: ``tools/list`` as ``__group__<name>`` stubs and can be reactivated by
#: the agent via :func:`activate_group` at runtime.
MINIMAL_DEACTIVATE_GROUPS: Dict[str, List[str]] = {
    "maya-scripting": ["extended"],
    "maya-scene": ["scene-management"],
}

# Backwards-compatibility aliases — ``server.py`` and tests previously
# referenced these as private module attributes.
_MINIMAL_SKILLS = MINIMAL_SKILLS
_MINIMAL_DEACTIVATE_GROUPS = MINIMAL_DEACTIVATE_GROUPS


def load_all_discovered_skills(server: Any) -> None:
    """Load every discovered skill (legacy ``minimal=False`` behaviour).

    Parameters
    ----------
    server:
        An :class:`McpHttpServer` instance — typically
        ``MayaMcpServer._server``.
    """
    try:
        skills = server.list_skills()
        for skill in skills:
            name = skill.name if hasattr(skill, "name") else skill["name"]
            try:
                server.load_skill(name)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to load skill %r: %s", name, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to list skills for full-load: %s", exc)


def load_minimal_skills(server: Any, skill_names: List[str]) -> None:
    """Load only ``skill_names`` and apply :data:`MINIMAL_DEACTIVATE_GROUPS`.

    For each skill in ``skill_names``:

    1. ``server.load_skill(name)`` — load the skill into the registry.
    2. For each group in :data:`MINIMAL_DEACTIVATE_GROUPS`\\ ``[name]``,
       call ``registry.set_group_enabled(group, False)`` so the tools
       collapse into a single ``__group__<group>`` stub.

    Skills not listed remain in ``Discovered`` state and appear as
    ``__skill__<name>`` stubs.
    """
    registry = server.registry
    for name in skill_names:
        try:
            server.load_skill(name)
            logger.info("[minimal] Loaded skill %r", name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[minimal] Failed to load skill %r: %s", name, exc)
            continue

        for group_name in MINIMAL_DEACTIVATE_GROUPS.get(name, []):
            try:
                count = registry.set_group_enabled(group_name, False)
                logger.info(
                    "[minimal] Deactivated group %r in %r (%d tools collapsed)",
                    group_name,
                    name,
                    count,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "[minimal] Failed to deactivate group %r in %r: %s",
                    group_name,
                    name,
                    exc,
                )
