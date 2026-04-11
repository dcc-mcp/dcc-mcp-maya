"""dcc_mcp_maya.api — High-level Maya skill authoring helpers.

This module provides a clean, unified interface for Maya skills developers.
Instead of repeating the same boilerplate in every script, import from here:

    from dcc_mcp_maya.api import maya_success, maya_error, maya_from_exception, require_cmds

Key helpers
-----------
``maya_success(message, **context)``
    Build a success ActionResultModel dict, identical to
    ``success_result(message, **context).to_dict()`` but without any extra
    import in the script body.

``maya_error(message, error, **context)``
    Build an error ActionResultModel dict.

``maya_from_exception(exc, message, **context)``
    Build an error ActionResultModel dict from a live exception, including the
    full traceback.  Prefer this over ``maya_error("...", str(exc))``.

``require_cmds()``
    Context manager that imports ``maya.cmds`` and returns it.  Raises
    ``ImportError`` (caught automatically by ``with_maya``) if Maya is not
    available.

``with_maya(func)``
    Decorator that wraps the entire function body in the standard
    try/ImportError/Exception pattern:

        @with_maya
        def create_sphere(radius: float = 1.0) -> dict:
            cmds = require_cmds()
            ...

    * ``ImportError``  → ``maya_error("Maya not available", ...)``
    * ``Exception``    → ``maya_from_exception(exc, ...)``

``MayaCmds``
    Type alias for ``maya.cmds`` module (for type annotations only).

Typical usage in a skill script::

    from dcc_mcp_maya.api import maya_success, maya_error, maya_from_exception

    import logging
    logger = logging.getLogger(__name__)

    def create_sphere(radius: float = 1.0) -> dict:
        try:
            import maya.cmds as cmds
            result = cmds.polySphere(radius=radius)
            return maya_success("Created sphere", object_name=result[0])
        except ImportError:
            return maya_error("Maya not available", "maya.cmds could not be imported")
        except Exception as exc:
            logger.exception("create_sphere failed")
            return maya_from_exception(exc, "Failed to create sphere")

Or with the decorator (even simpler)::

    from dcc_mcp_maya.api import with_maya, maya_success

    @with_maya
    def create_sphere(radius: float = 1.0) -> dict:
        import maya.cmds as cmds
        result = cmds.polySphere(radius=radius)
        return maya_success("Created sphere", object_name=result[0])
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import contextlib
import functools
import logging
from typing import Any, Callable, Generator, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Core result helpers
# ---------------------------------------------------------------------------


def maya_success(message: str, prompt: str | None = None, **context: Any) -> dict:
    """Return a success ActionResultModel as a plain dict.

    Thin wrapper around ``dcc_mcp_core.success_result`` so skill scripts do
    not need to import from two packages.

    Args:
        message: Human-readable success message.
        prompt: Optional follow-up hint shown to the AI agent.
        **context: Arbitrary key/value pairs stored in ``result["context"]``.

    Returns:
        Serialised ``ActionResultModel`` dict (``success=True``).

    Example::

        return maya_success("Created sphere", object_name="pSphere1", radius=1.0)
    """
    from dcc_mcp_core import success_result  # noqa: PLC0415

    return success_result(message, prompt=prompt, **context).to_dict()


def maya_error(
    message: str,
    error: str,
    prompt: str | None = None,
    possible_solutions: list[str] | None = None,
    **context: Any,
) -> dict:
    """Return an error ActionResultModel as a plain dict.

    Args:
        message: Short human-readable description of what went wrong.
        error: Detailed error string (e.g. exception message).
        prompt: Optional follow-up hint shown to the AI agent.
        possible_solutions: List of actionable fix suggestions shown to the agent.
        **context: Arbitrary key/value pairs stored in ``result["context"]``.

    Returns:
        Serialised ``ActionResultModel`` dict (``success=False``).

    Example::

        return maya_error(
            "Object not found",
            f"'{name}' does not exist in the scene",
            possible_solutions=["Check the object name", "Use list_objects to see available nodes"],
        )
    """
    from dcc_mcp_core import error_result  # noqa: PLC0415

    return error_result(
        message,
        error,
        prompt=prompt,
        possible_solutions=possible_solutions,
        **context,
    ).to_dict()


def maya_from_exception(
    exc: BaseException,
    message: str = "Maya operation failed",
    prompt: str | None = None,
    possible_solutions: list[str] | None = None,
    include_traceback: bool = True,
    **context: Any,
) -> dict:
    """Return an error ActionResultModel from a live exception.

    Unlike ``maya_error("...", str(exc))``, this captures the full traceback
    and passes it to the agent for richer diagnostics.

    Args:
        exc: The caught exception.
        message: Short description of the failed operation.
        prompt: Optional follow-up hint shown to the AI agent.
        possible_solutions: List of actionable fix suggestions.
        include_traceback: Whether to include the full Python traceback in
            the error detail (default ``True``).
        **context: Arbitrary key/value pairs stored in ``result["context"]``.

    Returns:
        Serialised ``ActionResultModel`` dict (``success=False``).

    Example::

        except Exception as exc:
            logger.exception("create_sphere failed")
            return maya_from_exception(exc, "Failed to create sphere")
    """
    from dcc_mcp_core import from_exception  # noqa: PLC0415

    return from_exception(
        error_message=str(exc),
        message=message,
        prompt=prompt,
        include_traceback=include_traceback,
        possible_solutions=possible_solutions,
        **context,
    ).to_dict()


# ---------------------------------------------------------------------------
# Maya availability helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def require_cmds() -> Generator[Any, None, None]:
    """Context manager that yields the ``maya.cmds`` module.

    Raises ``ImportError`` if Maya is not available.

    Example::

        with require_cmds() as cmds:
            cmds.polySphere(radius=1.0)
    """
    import maya.cmds as cmds  # noqa: PLC0415

    yield cmds


def get_cmds() -> Any:
    """Import and return ``maya.cmds``.

    Raises:
        ImportError: If Maya is not available in the current environment.

    Example::

        cmds = get_cmds()
        cmds.polySphere(radius=1.0)
    """
    import maya.cmds as cmds  # noqa: PLC0415

    return cmds


def is_maya_available() -> bool:
    """Return ``True`` if ``maya.cmds`` can be imported."""
    try:
        import maya.cmds  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

_MAYA_NOT_AVAILABLE_MSG = "Maya not available"
_MAYA_NOT_AVAILABLE_DETAIL = "maya.cmds could not be imported"
_MAYA_NOT_AVAILABLE_SOLUTIONS = [
    "Run this skill inside Maya (mayapy or Maya's Script Editor)",
    "Ensure Maya is properly installed and on the Python path",
]


def with_maya(func: F) -> F:
    """Decorator that wraps a skill function with the standard Maya error pattern.

    The decorated function is called normally.  Any exception is caught and
    converted to an ``ActionResultModel`` error dict:

    * ``ImportError``  → ``maya_error("Maya not available", ...)``
    * Any other ``Exception``  → ``maya_from_exception(exc, ...)``

    The wrapped function's name is used in the auto-generated error message
    so there is no need to pass a custom message.

    Example::

        from dcc_mcp_maya.api import with_maya, maya_success

        @with_maya
        def create_sphere(radius: float = 1.0) -> dict:
            import maya.cmds as cmds
            result = cmds.polySphere(radius=radius)
            return maya_success("Created sphere", object_name=result[0])

    .. note::
        The decorator does **not** log exceptions itself.  Add a
        ``logger.exception(...)`` call before ``return maya_from_exception``
        if you need structured logging.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict:
        try:
            return func(*args, **kwargs)
        except ImportError:
            return maya_error(
                _MAYA_NOT_AVAILABLE_MSG,
                _MAYA_NOT_AVAILABLE_DETAIL,
                possible_solutions=_MAYA_NOT_AVAILABLE_SOLUTIONS,
            )
        except Exception as exc:
            logger.exception("%s failed", func.__name__)
            return maya_from_exception(
                exc,
                message="Failed to execute {}".format(func.__name__),
            )

    return wrapper  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Convenience re-exports so callers only need one import
# ---------------------------------------------------------------------------

__all__ = [
    "maya_success",
    "maya_error",
    "maya_from_exception",
    "require_cmds",
    "get_cmds",
    "is_maya_available",
    "with_maya",
]
