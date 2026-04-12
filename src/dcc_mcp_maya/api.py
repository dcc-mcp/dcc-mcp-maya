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
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Sentinel used by require_param to detect "no default provided"
_SENTINEL = object()

# ---------------------------------------------------------------------------
# Core result helpers
# ---------------------------------------------------------------------------


def maya_success(message: str, prompt: Optional[str] = None, **context: Any) -> Dict[str, Any]:
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
    error: str = "",
    prompt: Optional[str] = None,
    possible_solutions: Optional[List[str]] = None,
    **context: Any,
) -> Dict[str, Any]:
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
    prompt: Optional[str] = None,
    possible_solutions: Optional[List[str]] = None,
    include_traceback: bool = True,
    **context: Any,
) -> Dict[str, Any]:
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
# Parameter helpers
# ---------------------------------------------------------------------------


class MissingParamError(ValueError):
    """Raised by :func:`require_param` when a required parameter is absent."""


def require_param(params: Any, key: str, default: Any = _SENTINEL) -> Any:
    """Extract a required (or defaulted) parameter from a *params* dict.

    Args:
        params: The ``params`` dict received by the skill ``run`` function.
        key: The parameter name to look up.
        default: If provided, return this value when *key* is absent.  When
            omitted the function raises :class:`MissingParamError`.

    Returns:
        The value associated with *key*, or *default* if supplied.

    Raises:
        MissingParamError: When *key* is absent and no *default* was given.

    Example::

        name = require_param(params, "name")          # raises if missing
        size = require_param(params, "size", 1.0)     # returns 1.0 if absent
    """
    if key in params:
        return params[key]
    if default is not _SENTINEL:
        return default
    raise MissingParamError("Required parameter '{}' is missing".format(key))


def missing_param_error(key: str, **context: Any) -> dict:
    """Return a pre-built error dict for a missing required parameter.

    Convenience wrapper so skill scripts can do::

        if "name" not in params:
            return missing_param_error("name")

    Args:
        key: The name of the missing parameter.
        **context: Extra context forwarded to :func:`maya_error`.

    Returns:
        Serialised ``ActionResultModel`` dict (``success=False``).
    """
    return maya_error(
        "Missing required parameter: '{}'".format(key),
        "The parameter '{}' must be provided".format(key),
        possible_solutions=["Pass '{}' in the params dict".format(key)],
        **context,
    )


# ---------------------------------------------------------------------------
# Node validation helpers
# ---------------------------------------------------------------------------


def validate_node_exists(cmds: Any, name: str) -> Optional[Dict[str, Any]]:
    """Return an error dict if *name* does not exist in the scene, else None.

    Designed for the common guard pattern::

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

    Args:
        cmds: The ``maya.cmds`` module (already imported by the caller).
        name: Maya node name to check.

    Returns:
        ``None`` when the node exists, otherwise a serialised error dict.
    """
    if not cmds.objExists(name):
        return maya_error(
            "Node not found: {}".format(name),
            "'{}' does not exist in the scene".format(name),
            possible_solutions=[
                "Use get_scene_info or list_scene_nodes to find valid node names",
                "Check for typos in the node name",
            ],
        )
    return None


def validate_node_type(cmds: Any, name: str, expected_type: str) -> Optional[Dict[str, Any]]:
    """Return an error dict if *name* is not of *expected_type*, else None.

    Args:
        cmds: The ``maya.cmds`` module.
        name: Maya node name.
        expected_type: Expected Maya node type string (e.g. ``"transform"``,
            ``"mesh"``, ``"displayLayer"``).

    Returns:
        ``None`` when the type matches, otherwise a serialised error dict.

    Example::

        err = validate_node_type(cmds, layer_name, "displayLayer")
        if err:
            return err
    """
    actual = cmds.objectType(name)
    if actual != expected_type:
        return maya_error(
            "Wrong node type: {}".format(name),
            "'{}' is a '{}', expected '{}'".format(name, actual, expected_type),
            possible_solutions=[
                "Use get_scene_info to inspect the node type",
                "Provide a '{}' node instead".format(expected_type),
            ],
        )
    return None


def batch_validate_nodes(cmds: Any, names: List[str]) -> Optional[Dict[str, Any]]:
    """Return an error dict if any node in *names* does not exist, else None.

    A convenience wrapper around :func:`validate_node_exists` for the common
    case where a skill function needs to validate multiple nodes before
    proceeding.

    Args:
        cmds: The ``maya.cmds`` module (already imported by the caller).
        names: Sequence of Maya node names to check.

    Returns:
        ``None`` when **all** nodes exist, otherwise a serialised error dict
        for the **first** missing node.

    Example::

        err = batch_validate_nodes(cmds, [source_mesh, target_mesh])
        if err:
            return err
    """
    for name in names:
        err = validate_node_exists(cmds, name)
        if err is not None:
            return err
    return None


# ---------------------------------------------------------------------------
# Additional parameter helpers
# ---------------------------------------------------------------------------


def require_any_param(params: Any, *keys: str) -> Any:
    """Return the value of the first key found in *params*.

    Useful when a skill accepts several mutually-exclusive parameter names
    that map to the same concept (e.g. ``name`` vs ``node_name``).

    Args:
        params: The ``params`` dict received by the skill ``run`` function.
        *keys: One or more parameter names to search for, in order.

    Returns:
        The value associated with the first matching key.

    Raises:
        MissingParamError: When **none** of the supplied keys exist in *params*.

    Example::

        node = require_any_param(params, "name", "node_name", "object_name")
    """
    for key in keys:
        if key in params:
            return params[key]
    raise MissingParamError("At least one of {} is required".format(", ".join("'{}'".format(k) for k in keys)))


def get_param_list(params: Any, key: str, default: Any = None) -> List[Any]:
    """Extract a list parameter, coercing a bare string to a one-element list.

    Many Maya skills accept either a single name or a list of names.  This
    helper normalises both forms so the skill body only needs to handle lists.

    Args:
        params: The ``params`` dict received by the skill ``run`` function.
        key: The parameter name to look up.
        default: Value to return when *key* is absent.  Defaults to an empty
            list (``[]``) when ``None`` is given.

    Returns:
        A list.  If the value is already a list it is returned as-is; if it
        is a string it is wrapped in ``[value]``; otherwise it is cast with
        ``list(value)``.

    Example::

        meshes = get_param_list(params, "meshes")          # [] if absent
        objects = get_param_list(params, "objects", [])    # [] if absent
        joints = get_param_list(params, "joints")          # handles "joint1" or ["joint1","joint2"]
    """
    if default is None:
        default = []
    value = params.get(key, default)
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


# ---------------------------------------------------------------------------
# Cross-DCC protocol data model helpers (dcc-mcp-core v0.12+)
# ---------------------------------------------------------------------------


def scene_object_from_node(cmds: Any, long_name: str) -> Dict[str, Any]:
    """Build a ``SceneObject``-compatible dict from a Maya DAG transform node.

    Maps Maya node attributes to the cross-DCC ``SceneObject`` schema so that
    callers do not need to know the exact ``dcc_mcp_core.SceneObject`` constructor.

    The returned dict has the following keys that mirror ``SceneObject`` fields:
    ``name``, ``long_name``, ``object_type``, ``parent``, ``visible``, ``metadata``.

    Args:
        cmds: The ``maya.cmds`` module (already imported by the caller).
        long_name: Full DAG path of the transform node (e.g. ``"|group1|pSphere1"``).

    Returns:
        Dict compatible with ``SceneObject`` field layout.

    Example::

        obj = scene_object_from_node(cmds, "|group1|pSphere1")
        # {"name": "pSphere1", "long_name": "|group1|pSphere1",
        #  "object_type": "transform", "parent": "|group1",
        #  "visible": True, "metadata": {}}
    """
    parent_list = cmds.listRelatives(long_name, parent=True, fullPath=True) or []
    try:
        visible = bool(cmds.getAttr("{}.visibility".format(long_name)))
    except Exception:
        visible = True
    return {
        "name": long_name.split("|")[-1],
        "long_name": long_name,
        "object_type": cmds.objectType(long_name),
        "parent": parent_list[0] if parent_list else None,
        "visible": visible,
        "metadata": {},
    }


def object_transform_from_node(cmds: Any, node_name: str) -> Dict[str, Any]:
    """Build an ``ObjectTransform``-compatible dict from a Maya node's TRS.

    Maya uses a right-hand Y-up coordinate system which matches the
    ``ObjectTransform`` convention directly (no axis remapping needed).

    The returned dict has keys ``translate``, ``rotate``, ``scale`` — each
    a list of three floats — matching the ``ObjectTransform`` field layout.

    Args:
        cmds: The ``maya.cmds`` module (already imported by the caller).
        node_name: Name or full DAG path of the transform node.

    Returns:
        Dict compatible with ``ObjectTransform`` field layout.

    Example::

        xform = object_transform_from_node(cmds, "pSphere1")
        # {"translate": [0.0, 1.0, 0.0], "rotate": [0.0, 0.0, 0.0],
        #  "scale": [1.0, 1.0, 1.0]}
    """
    translate = list(cmds.getAttr("{}.translate".format(node_name))[0])
    rotate = list(cmds.getAttr("{}.rotate".format(node_name))[0])
    scale = list(cmds.getAttr("{}.scale".format(node_name))[0])
    return {"translate": translate, "rotate": rotate, "scale": scale}


def bounding_box_from_node(cmds: Any, node_name: str) -> Dict[str, Any]:
    """Build a ``BoundingBox``-compatible dict from a Maya node's world bbox.

    Uses ``cmds.exactWorldBoundingBox`` which returns the tight axis-aligned
    bounding box in world space.

    The returned dict has keys ``min``, ``max``, ``center``, ``size`` — each
    a list of three floats — matching the ``BoundingBox`` field layout plus
    the convenience helpers ``BoundingBox.center()`` and ``BoundingBox.size()``.

    Args:
        cmds: The ``maya.cmds`` module (already imported by the caller).
        node_name: Name or full DAG path of the node.

    Returns:
        Dict compatible with ``BoundingBox`` field layout.

    Example::

        bb = bounding_box_from_node(cmds, "pSphere1")
        # {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0],
        #  "center": [0.0, 0.0, 0.0], "size": [2.0, 2.0, 2.0]}
    """
    bb = cmds.exactWorldBoundingBox(node_name)
    # bb = [xmin, ymin, zmin, xmax, ymax, zmax]
    bb_min = [bb[0], bb[1], bb[2]]
    bb_max = [bb[3], bb[4], bb[5]]
    center = [(bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0]
    size = [bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]]
    return {"min": bb_min, "max": bb_max, "center": center, "size": size}


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
    # Parameter helpers
    "require_param",
    "require_any_param",
    "get_param_list",
    "missing_param_error",
    "MissingParamError",
    # Node validation helpers
    "validate_node_exists",
    "validate_node_type",
    "batch_validate_nodes",
    # Cross-DCC data model helpers
    "scene_object_from_node",
    "object_transform_from_node",
    "bounding_box_from_node",
]
