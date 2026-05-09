"""dcc_mcp_maya.api — High-level Maya skill authoring helpers.

This module provides a clean, unified interface for Maya skills developers.
Instead of repeating the same boilerplate in every script, import from here:

    from dcc_mcp_maya.api import maya_success, maya_error, maya_from_exception, require_cmds

Key helpers
-----------
``maya_success(message, **context)``
    Build a success result dict backed by ``dcc_mcp_core.skill.skill_success``
    (pure-Python, zero compiled-extension dependency).

``maya_error(message, error, **context)``
    Build an error ToolResult dict.

``maya_from_exception(exc, message, **context)``
    Build an error ToolResult dict from a live exception, including the
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

# Import third-party modules
from dcc_mcp_core.schema import derive_schema
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success, skill_warning

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Sentinel used by require_param to detect "no default provided"
_SENTINEL = object()

# ---------------------------------------------------------------------------
# Core result helpers
# ---------------------------------------------------------------------------


def maya_success(message: str, prompt: Optional[str] = None, **context: Any) -> Dict[str, Any]:
    """Return a success ToolResult as a plain dict.

    Thin wrapper around ``dcc_mcp_core.success_result`` so skill scripts do
    not need to import from two packages.

    Args:
        message: Human-readable success message.
        prompt: Optional follow-up hint shown to the AI agent.
        **context: Arbitrary key/value pairs stored in ``result["context"]``.

    Returns:
        Serialised ``ToolResult`` dict (``success=True``).

    Example::

        return maya_success("Created sphere", object_name="pSphere1", radius=1.0)
    """
    return skill_success(message, prompt=prompt, **context)


def maya_error(
    message: str,
    error: str = "",
    prompt: Optional[str] = None,
    possible_solutions: Optional[List[str]] = None,
    **context: Any,
) -> Dict[str, Any]:
    """Return an error ToolResult as a plain dict.

    Args:
        message: Short human-readable description of what went wrong.
        error: Detailed error string (e.g. exception message).
        prompt: Optional follow-up hint shown to the AI agent.
        possible_solutions: List of actionable fix suggestions shown to the agent.
        **context: Arbitrary key/value pairs stored in ``result["context"]``.

    Returns:
        Serialised ``ToolResult`` dict (``success=False``).

    Example::

        return maya_error(
            "Object not found",
            f"'{name}' does not exist in the scene",
            possible_solutions=["Check the object name", "Use list_objects to see available nodes"],
        )
    """
    return skill_error(
        message,
        error,
        prompt=prompt,
        possible_solutions=possible_solutions,
        **context,
    )


def maya_warning(message: str, warning: str = "", prompt: Optional[str] = None, **context: Any) -> Dict[str, Any]:
    """Return a success ToolResult dict with a warning note.

    The result is a *success* (``success=True``) but includes a ``warning``
    key in the context to inform the AI agent of a non-fatal issue.

    Corresponds to ``dcc_mcp_core.skill.skill_warning``.

    Args:
        message: Human-readable success message.
        warning: Short description of the non-fatal warning.
        prompt: Optional follow-up hint shown to the AI agent.
        **context: Arbitrary key/value pairs stored in ``result["context"]``.

    Returns:
        Serialised ``ToolResult`` dict (``success=True``, with
        ``context["warning"]`` set).

    Example::

        return maya_warning(
            "Material assigned with fallback",
            warning="Arnold not available; used Lambert instead",
            prompt="Install Arnold for physically-based shading.",
            object_name="pSphere1",
        )
    """
    return skill_warning(message, warning=warning, prompt=prompt, **context)


def maya_from_exception(
    exc: BaseException,
    message: str = "Maya operation failed",
    prompt: Optional[str] = None,
    possible_solutions: Optional[List[str]] = None,
    include_traceback: bool = True,
    **context: Any,
) -> Dict[str, Any]:
    """Return an error ToolResult from a live exception.

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
        Serialised ``ToolResult`` dict (``success=False``).

    Example::

        except Exception as exc:
            logger.exception("create_sphere failed")
            return maya_from_exception(exc, "Failed to create sphere")
    """
    return skill_exception(
        exc,
        message=message,
        prompt=prompt,
        include_traceback=include_traceback,
        possible_solutions=possible_solutions,
        **context,
    )


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
    converted to a ``ToolResult`` error dict:

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
        Serialised ``ToolResult`` dict (``success=False``).
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
# Name and context helpers
# ---------------------------------------------------------------------------


def ensure_valid_name(name: Any, param: str = "name") -> Optional[Dict[str, Any]]:
    """Return an error dict if *name* is falsy or whitespace-only, else None.

    Designed to guard skill functions that require a non-empty node name::

        err = ensure_valid_name(layer_name, "layer_name")
        if err:
            return err

    Args:
        name: The value to validate (typically a ``str``).
        param: The parameter name used in the error message.

    Returns:
        ``None`` when *name* is a non-empty string, otherwise a serialised
        error dict.
    """
    if not name or (isinstance(name, str) and not name.strip()):
        return maya_error(
            "Invalid '{}': name must not be empty".format(param),
            "'{}' received an empty or whitespace-only value".format(param),
            possible_solutions=[
                "Pass a non-empty string for '{}'".format(param),
            ],
        )
    return None


def build_context_dict(**kwargs: Any) -> Dict[str, Any]:
    """Return a dict of *kwargs* with ``None``-valued keys removed.

    Reduces ``if value is not None`` boilerplate in skill return statements::

        return maya_success("Done", prompt="...", **build_context_dict(
            object_name=name,
            translate=translate,  # may be None
        ))

    Args:
        **kwargs: Arbitrary key/value pairs.

    Returns:
        A new dict containing only entries whose value is not ``None``.
    """
    return {k: v for k, v in kwargs.items() if v is not None}


# ---------------------------------------------------------------------------
# Cross-DCC data model helpers
# ---------------------------------------------------------------------------


def scene_object_from_node(cmds: Any, long_name: str) -> Dict[str, Any]:
    """Build a SceneObject-compatible dict from a Maya DAG transform node.

    Returns a dictionary matching the ``SceneObject`` schema used by
    ``dcc-mcp-core`` for cross-DCC scene exchange::

        {
            "name": "pSphere1",
            "long_name": "|pSphere1",
            "object_type": "transform",
            "parent": None,
            "visible": True,
            "metadata": {},
        }

    Args:
        cmds: The ``maya.cmds`` module.
        long_name: Long DAG path of the node (e.g. ``"|group1|pSphere1"``).

    Returns:
        SceneObject-compatible dict.
    """
    short_name = long_name.rsplit("|", 1)[-1] if "|" in long_name else long_name
    object_type = cmds.objectType(long_name)

    # Determine parent (None for top-level transforms)
    parents = cmds.listRelatives(long_name, parent=True, fullPath=True) or []
    parent = parents[0] if parents else None

    # Visibility — graceful fallback
    try:
        visible = bool(cmds.getAttr("{}.visibility".format(long_name)))
    except Exception:
        visible = True

    return {
        "name": short_name,
        "long_name": long_name,
        "object_type": object_type,
        "parent": parent,
        "visible": visible,
        "metadata": {},
    }


def object_transform_from_node(cmds: Any, node_name: str) -> Dict[str, Any]:
    """Build an ObjectTransform-compatible dict from a Maya transform node.

    Returns::

        {
            "translate": [tx, ty, tz],
            "rotate":    [rx, ry, rz],
            "scale":     [sx, sy, sz],
        }

    All values are Python ``float``.

    Args:
        cmds: The ``maya.cmds`` module.
        node_name: Name of the transform node.

    Returns:
        ObjectTransform-compatible dict.
    """
    tx, ty, tz = cmds.getAttr("{}.translate".format(node_name))[0]
    rx, ry, rz = cmds.getAttr("{}.rotate".format(node_name))[0]
    sx, sy, sz = cmds.getAttr("{}.scale".format(node_name))[0]
    return {
        "translate": [float(tx), float(ty), float(tz)],
        "rotate": [float(rx), float(ry), float(rz)],
        "scale": [float(sx), float(sy), float(sz)],
    }


def bounding_box_from_node(cmds: Any, node_name: str) -> Dict[str, Any]:
    """Build a BoundingBox-compatible dict from a Maya node.

    Uses ``exactWorldBoundingBox`` to compute the world-space AABB.

    Returns::

        {
            "min":    [xmin, ymin, zmin],
            "max":    [xmax, ymax, zmax],
            "center": [cx,   cy,   cz  ],
            "size":   [dx,   dy,   dz  ],
        }

    Args:
        cmds: The ``maya.cmds`` module.
        node_name: Name of the node.

    Returns:
        BoundingBox-compatible dict.
    """
    bb = cmds.exactWorldBoundingBox(node_name)
    xmin, ymin, zmin, xmax, ymax, zmax = (float(v) for v in bb)
    cx = (xmin + xmax) / 2.0
    cy = (ymin + ymax) / 2.0
    cz = (zmin + zmax) / 2.0
    return {
        "min": [xmin, ymin, zmin],
        "max": [xmax, ymax, zmax],
        "center": [cx, cy, cz],
        "size": [xmax - xmin, ymax - ymin, zmax - zmin],
    }


# ---------------------------------------------------------------------------
# Convenience re-exports so callers only need one import
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Typed-output helper (dcc-mcp-core#242, 0.14.22) -----------------------------
# ---------------------------------------------------------------------------
#
# Motivation
#   * ``tools/list`` on the per-DCC MCP server emits ``outputSchema`` only
#     when the upstream ToolSpec was registered with one — today
#     (core 0.14.22) tools.yaml's ``outputSchema`` key is silently dropped
#     and there is no Python-level API to mutate a registered action's
#     ``output_schema`` field without re-registering it in full.
#   * Until core grows that propagation path, skill authors can still get
#     typed-output semantics into the envelope agents actually receive:
#     attach a ``derive_schema``-derived JSON Schema and a serialised
#     representation of the dataclass/``TypedDict`` on the result dict.
#   * Agents that speak the forward-compatible ``outputSchema`` key
#     (core's own ``McpClient`` does, as do the REST ``/v1/call``
#     envelopes scheduled for #660) can then validate returned data
#     without the server ever having to grow a new MCP surface.
#
# Design (SOLID)
#   * Single responsibility — builds a forward-compat dict, nothing else.
#     No IO, no Maya imports, no registry mutation.
#   * Dependency injection — ``_schema_deriver`` can be swapped in tests.
#   * Open/closed — if/when core propagates tools.yaml ``outputSchema``
#     we can layer the registry-side hook on top without touching skill
#     scripts that already use :func:`maya_typed_success`.
# ---------------------------------------------------------------------------


def _default_schema_deriver(tp: Any) -> Optional[Dict[str, Any]]:
    """Default schema deriver using core's ``derive_schema``."""
    try:
        schema = derive_schema(tp)
    except Exception:  # noqa: BLE001 — never fail a skill over schema derivation
        return None
    return schema if isinstance(schema, dict) else None


def _default_as_plain_dict(value: Any) -> Dict[str, Any]:
    """Convert a dataclass / ``TypedDict`` / plain-dict value to a dict.

    Keeps the helper dependency-free: falls back to ``vars(value)`` for
    simple objects with a ``__dict__`` and to a single-key wrapper for
    plain scalars so the caller always receives a JSON-serialisable dict.
    """
    if isinstance(value, dict):
        return dict(value)
    try:
        from dataclasses import asdict, is_dataclass  # noqa: PLC0415

        if is_dataclass(value):
            return asdict(value)
    except Exception:  # noqa: BLE001
        pass
    if hasattr(value, "_asdict"):  # namedtuple
        try:
            return dict(value._asdict())
        except Exception:  # noqa: BLE001
            pass
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return {"value": value}


def maya_typed_success(
    message: str,
    data: Any,
    return_type: Optional[Any] = None,
    *,
    prompt: Optional[str] = None,
    _schema_deriver: Optional[Any] = None,
    _to_dict: Optional[Any] = None,
    **context: Any,
) -> Dict[str, Any]:
    """Build a success envelope augmented with an ``outputSchema`` hint.

    A forward-compatible sibling of :func:`maya_success` that:

    1. Serialises ``data`` (usually a ``@dataclass`` instance) into a
       plain dict via :func:`_default_as_plain_dict`.
    2. Derives a JSON Schema from ``return_type`` (defaulting to
       ``type(data)``) via :func:`dcc_mcp_core.schema.derive_schema`.
    3. Attaches the schema to the result's ``context`` under the
       ``output_schema`` key so agents can validate the payload even
       before upstream core propagates tools.yaml ``outputSchema``.

    Parameters
    ----------
    message:
        Human-readable success message.
    data:
        The typed result (dataclass instance, ``TypedDict``, ``namedtuple``,
        or any ``__dict__``-friendly object).
    return_type:
        Explicit type to derive the schema from; defaults to
        ``type(data)``.  Use this when ``data`` is a ``dict`` that
        conforms to a ``TypedDict`` (``type(data)`` would just yield
        ``dict``).
    prompt, context:
        Forwarded to :func:`maya_success` verbatim.
    _schema_deriver, _to_dict:
        Injection seams for unit tests.  Callers should not use them.

    Returns
    -------
    dict
        ``maya_success``-compatible envelope with two extra context keys:
        ``output_schema`` (the JSON Schema) and ``typed_result`` (the
        serialised data dict).  Both are omitted gracefully when
        derivation fails so the helper never breaks a skill.
    """
    schema_fn = _schema_deriver or _default_schema_deriver
    to_dict_fn = _to_dict or _default_as_plain_dict

    tp = return_type if return_type is not None else type(data)
    schema = schema_fn(tp)
    payload = to_dict_fn(data)

    enriched: Dict[str, Any] = dict(context)
    if schema is not None:
        enriched["output_schema"] = schema
    if payload:
        enriched["typed_result"] = payload
    return maya_success(message, prompt=prompt, **enriched)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "maya_success",
    "maya_error",
    "maya_warning",
    "maya_from_exception",
    "maya_typed_success",
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
    # Name and context helpers
    "ensure_valid_name",
    "build_context_dict",
    # Cross-DCC data model helpers
    "scene_object_from_node",
    "object_transform_from_node",
    "bounding_box_from_node",
    # DCC capabilities
    "maya_capabilities",
]

# Import maya_capabilities here so it is accessible as dcc_mcp_maya.api.maya_capabilities
from dcc_mcp_maya.capabilities import maya_capabilities  # noqa: E402, F401
