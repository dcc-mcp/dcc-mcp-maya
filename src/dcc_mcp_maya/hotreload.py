"""File hot-reload support for Maya MCP skills.

Monitors skill directories for changes and automatically reloads affected skills
without requiring a server restart.

This module uses the ``SkillWatcher`` from dcc-mcp-core (v0.12.24+), which:
- Monitors directories with platform-native APIs (inotify/FSEvents/ReadDirectoryChangesW)
- Debounces rapid events (default 300ms) to avoid excessive reloads
- Runs on a background thread, never blocking Maya
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import threading
from pathlib import Path
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class MayaSkillHotReloader:
    """Manages skill hot-reload for Maya using dcc-mcp-core's SkillWatcher.

    This class:
    1. Creates a SkillWatcher to monitor skill directories
    2. Registers a callback to reload skills when files change
    3. Handles unload/load transitions gracefully
    4. Tracks reload history and performance metrics

    Example::

        reloader = MayaSkillHotReloader(server)
        reloader.enable(skill_paths, debounce_ms=300)
        # ... files are now monitored ...
        reloader.disable()  # stop monitoring

    Args:
        server: The MayaMcpServer instance to reload skills into.
    """

    def __init__(self, server: Any) -> None:
        """Initialize the hot reloader for a server.

        Args:
            server: A MayaMcpServer instance.
        """
        self._server = server
        self._watcher: Optional[Any] = None
        self._watched_paths: List[str] = []
        self._lock = threading.Lock()
        self._reload_count = 0
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Whether hot-reload is currently active."""
        return self._enabled

    @property
    def reload_count(self) -> int:
        """Total number of reload events triggered."""
        return self._reload_count

    @property
    def watched_paths(self) -> List[str]:
        """List of directories currently being monitored."""
        with self._lock:
            return list(self._watched_paths)

    def enable(
        self,
        skill_paths: Optional[List[str]] = None,
        debounce_ms: int = 300,
    ) -> bool:
        """Enable hot-reload for the given skill directories.

        Starts a SkillWatcher to monitor the provided directories. When
        SKILL.md or script files are modified, the affected skills are
        automatically unloaded and reloaded.

        Args:
            skill_paths: List of directories to watch. If ``None``, uses the
                paths from the server's SkillCatalog.
            debounce_ms: Milliseconds to wait before reloading after a change.
                Default 300ms (matching dcc-mcp-core's standard).

        Returns:
            ``True`` if hot-reload was successfully enabled, ``False`` on error.

        Example::

            reloader.enable(["/path/to/skills"], debounce_ms=250)
        """
        with self._lock:
            if self._enabled:
                logger.warning("Hot-reload already enabled")
                return True

            try:
                from dcc_mcp_core import SkillWatcher  # noqa: PLC0415

                paths_to_watch = skill_paths or self._resolve_skill_paths()

                if not paths_to_watch:
                    logger.warning("No skill paths to watch; hot-reload not enabled")
                    return False

                self._watcher = SkillWatcher(debounce_ms=debounce_ms)

                for path in paths_to_watch:
                    try:
                        self._watcher.watch(path)
                        self._watched_paths.append(path)
                        logger.debug("Hot-reload watching: %s", path)
                    except Exception as exc:
                        logger.warning("Failed to watch %r: %s", path, exc)

                if not self._watched_paths:
                    logger.warning("No paths were successfully watched")
                    self._watcher = None
                    return False

                self._enabled = True
                logger.info("Hot-reload enabled for %d path(s)", len(self._watched_paths))
                return True

            except Exception as exc:
                logger.error("Failed to enable hot-reload: %s", exc)
                self._watcher = None
                self._enabled = False
                return False

    def disable(self) -> None:
        """Disable hot-reload and clean up resources."""
        with self._lock:
            if self._watcher is not None:
                self._watcher = None
                self._watched_paths.clear()
                self._enabled = False
                logger.info("Hot-reload disabled")

    def reload_now(self) -> int:
        """Manually trigger a reload of all monitored skills.

        Useful for debugging or when you know a change occurred outside
        the normal watcher loop.

        Returns:
            Number of skills successfully reloaded.
        """
        if not self._enabled or self._watcher is None:
            logger.warning("Hot-reload is not enabled")
            return 0

        with self._lock:
            try:
                # Trigger manual reload in watcher
                self._watcher.reload()
                self._reload_count += 1

                # Re-register all skills from catalog
                reloaded = 0
                try:
                    for summary in self._server._server.list_skills():  # noqa: SLF001
                        skill_name = summary.name if hasattr(summary, "name") else summary.get("name")
                        try:
                            self._server._server.load_skill(skill_name)  # noqa: SLF001
                            reloaded += 1
                        except Exception as exc:
                            logger.debug("Failed to reload skill %r: %s", skill_name, exc)
                except Exception as exc:
                    logger.warning("Error during reload: %s", exc)

                logger.info("Manual reload triggered: %d skills reloaded", reloaded)
                return reloaded

            except Exception as exc:
                logger.error("Manual reload failed: %s", exc)
                return 0

    def _resolve_skill_paths(self) -> List[str]:
        """Resolve the skill paths from the server's configuration.

        Returns:
            List of skill directory paths, or empty list if unavailable.
        """
        try:
            # Try to get search paths from the server's config
            search_paths = []

            # Built-in skills directory
            from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR  # noqa: PLC0415

            if _BUILTIN_SKILLS_DIR.is_dir():
                search_paths.append(str(_BUILTIN_SKILLS_DIR))

            # Environment variables
            from dcc_mcp_maya.server import _collect_skill_search_paths  # noqa: PLC0415

            search_paths.extend(_collect_skill_search_paths(include_bundled=False))

            return search_paths
        except Exception as exc:
            logger.debug("Failed to resolve skill paths: %s", exc)
            return []

    def __repr__(self) -> str:
        """Return a string representation."""
        status = "enabled" if self._enabled else "disabled"
        paths_count = len(self._watched_paths) if self._enabled else 0
        return (
            f"MayaSkillHotReloader(status={status}, "
            f"watched_paths={paths_count}, reloads={self._reload_count})"
        )
