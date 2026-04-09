"""Built-in Maya actions for the MCP server.

Progressive discovery & registration
--------------------------------------
Actions are loaded in two phases that mirror ``dcc-mcp-core``'s
``scan_and_load`` SOP:

1. **Discovery** — :func:`discover_action_modules` walks every ``*.py``
   module in this package and collects callables that look like action
   functions (return a dict, accept only keyword-safe parameters).

2. **Registration** — :func:`register_all` iterates the discovered
   functions and registers each one with the ``ActionRegistry``.  If a
   module fails to import (e.g. missing optional Maya plugin), it is
   **skipped gracefully** rather than crashing the server.

This means adding a new action file is as simple as dropping a ``*.py``
module into this directory — no edits to ``__init__.py`` are required.

Action module contract
----------------------
Each module **must** expose a ``_ACTIONS`` list of ``(name, description,
category, tags)`` tuples that describe the actions it provides.  The
callable itself must live at module scope under the same ``name``.

Example::

    # src/dcc_mcp_maya/actions/my_module.py
    _ACTIONS = [
        ("my_action", "Does something useful", "utility", ["tag1"]),
    ]

    def my_action(**kwargs):
        ...
        return {"success": True, "message": "...", "context": {}}
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING, Dict, List, Tuple

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public re-exports kept for backward compatibility with direct imports.
# These cover the original "core" set that shipped with main branch.
# ---------------------------------------------------------------------------

from dcc_mcp_maya.actions.primitives import (  # noqa: E402
    create_cube,
    create_cylinder,
    create_sphere,
    delete_objects,
    set_transform,
)
from dcc_mcp_maya.actions.scene import (  # noqa: E402
    get_selection,
    get_session_info,
    list_objects,
    new_scene,
    open_scene,
    save_scene,
    set_selection,
)
from dcc_mcp_maya.actions.scripting import execute_mel, execute_python  # noqa: E402

__all__ = [
    # scene (core)
    "new_scene",
    "save_scene",
    "open_scene",
    "list_objects",
    "get_selection",
    "set_selection",
    "get_session_info",
    # primitives (core)
    "create_sphere",
    "create_cube",
    "create_cylinder",
    "delete_objects",
    "set_transform",
    # scripting (core)
    "execute_mel",
    "execute_python",
    # discovery helpers
    "discover_action_modules",
    "register_all",
]

# ---------------------------------------------------------------------------
# Progressive discovery
# ---------------------------------------------------------------------------

# Modules that are part of the built-in action set shipped with this package.
# Order matters for deterministic registration — core modules first, then
# extended modules in alphabetical order.
_CORE_MODULES = [
    "scene",
    "primitives",
    "scripting",
]


def discover_action_modules() -> List[Tuple[str, List]]:
    """Discover all action modules in this package.

    Walks every importable ``*.py`` sub-module under ``dcc_mcp_maya.actions``
    and collects those that expose a ``_ACTIONS`` list.  Import errors are
    caught and logged at WARNING level so a broken optional module never
    prevents the core set from loading.

    Returns:
        A list of ``(module_name, _ACTIONS)`` pairs in stable order:
        core modules first, then remaining modules alphabetically.
    """
    import dcc_mcp_maya.actions as _pkg  # noqa: PLC0415

    pkg_path = _pkg.__path__
    pkg_name = _pkg.__name__

    # Collect all sub-module names (excluding __init__ itself)
    available: List[str] = []
    for _, mod_name, is_pkg in pkgutil.iter_modules(pkg_path):
        if not is_pkg and mod_name != "__init__":
            available.append(mod_name)

    # Stable order: core first, then the rest alphabetically
    core_set = set(_CORE_MODULES)
    ordered = _CORE_MODULES + sorted(m for m in available if m not in core_set)

    results: List[Tuple[str, List]] = []
    for mod_name in ordered:
        full_name = f"{pkg_name}.{mod_name}"
        try:
            mod = importlib.import_module(full_name)
        except Exception as exc:
            logger.warning("Skipping action module %s: %s", full_name, exc)
            continue

        actions = getattr(mod, "_ACTIONS", None)
        if actions is None:
            logger.debug("Module %s has no _ACTIONS list, skipping", full_name)
            continue

        results.append((mod_name, actions))
        logger.debug("Discovered %d action(s) in %s", len(actions), full_name)

    return results


def register_all(registry) -> Dict[str, int]:
    """Discover and register all built-in Maya actions into *registry*.

    Uses :func:`discover_action_modules` to progressively find every action
    module, then registers each action with the ``ActionRegistry``.

    Args:
        registry: An ``ActionRegistry`` instance from ``dcc_mcp_core``.

    Returns:
        A summary dict ``{module_name: action_count}`` for observability.
    """
    summary: Dict[str, int] = {}
    discovered = discover_action_modules()

    for mod_name, actions in discovered:
        count = 0
        for entry in actions:
            name, description, category, tags = entry
            try:
                registry.register(
                    name,
                    description=description,
                    category=category,
                    tags=tags,
                    dcc="maya",
                    version="1.0.0",
                )
                count += 1
            except Exception as exc:
                logger.warning("Failed to register action %r from %s: %s", name, mod_name, exc)

        summary[mod_name] = count
        logger.debug("Registered %d/%d action(s) from module %s", count, len(actions), mod_name)

    total = sum(summary.values())
    logger.info("Maya actions registered: %d total across %d modules", total, len(summary))
    return summary
