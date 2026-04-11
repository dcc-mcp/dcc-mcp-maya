"""Maya file reference management actions.

Provides actions to create, query and remove file references in a Maya scene,
enabling an Agent to work with multi-file workflows (e.g. referencing characters,
environments or props into a shot scene).
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_reference(
    file_path: str,
    namespace: Optional[str] = None,
    group_reference: bool = False,
) -> dict:
    """Reference an external Maya file into the current scene.

    Args:
        file_path: Absolute path to the Maya file to reference (.ma, .mb).
        namespace: Namespace string to use.  When omitted Maya derives one from
            the filename.  Use ``":"`` for the root namespace (not recommended).
        group_reference: If True, place the referenced nodes inside a new
            transform group node.  Default: False.

    Returns:
        ActionResultModel dict with ``context.reference_node``,
        ``context.namespace``, and ``context.file_path``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not file_path or not file_path.strip():
            return error_result("Invalid file path", "file_path must not be empty").to_dict()

        kwargs = {
            "reference": True,
            "groupReference": group_reference,
            "mergeNamespacesOnClash": False,
            "returnNewNodes": False,
        }
        if namespace is not None:
            kwargs["namespace"] = namespace
        else:
            kwargs["defaultNamespace"] = False

        # cmds.file returns the reference node name
        ref_node = cmds.file(file_path, **kwargs)

        # Resolve actual namespace used
        try:
            resolved_ns = cmds.referenceQuery(ref_node, namespace=True, shortName=True)
        except Exception:
            resolved_ns = namespace or ""

        return success_result(
            "Referenced '{}' as '{}'".format(file_path, resolved_ns),
            reference_node=ref_node,
            namespace=resolved_ns,
            file_path=file_path,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_reference failed")
        return error_result("Failed to reference file '{}'".format(file_path), str(exc)).to_dict()


def list_references() -> dict:
    """List all file references in the current scene.

    Returns:
        ActionResultModel dict with ``context.references`` — a list of dicts
        with ``reference_node``, ``file_path``, ``namespace``, and ``loaded``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ref_nodes = cmds.ls(type="reference") or []
        # Filter out the built-in sharedReferenceNode
        ref_nodes = [r for r in ref_nodes if r != "sharedReferenceNode"]

        references = []
        for ref_node in ref_nodes:
            try:
                file_path = cmds.referenceQuery(ref_node, filename=True, withoutCopyNumber=True)
                namespace = cmds.referenceQuery(ref_node, namespace=True, shortName=True)
                loaded = cmds.referenceQuery(ref_node, isLoaded=True)
            except Exception:
                continue
            references.append(
                {
                    "reference_node": ref_node,
                    "file_path": file_path,
                    "namespace": namespace,
                    "loaded": loaded,
                }
            )

        return success_result(
            "Found {} reference(s)".format(len(references)),
            references=references,
            count=len(references),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_references failed")
        return error_result("Failed to list references", str(exc)).to_dict()


def remove_reference(
    reference_node: str,
    remove_namespace: bool = True,
) -> dict:
    """Remove a file reference from the current scene.

    Args:
        reference_node: Name of the reference node to remove (e.g.
            ``"characterRN"``).  Use :func:`list_references` to discover
            available reference nodes.
        remove_namespace: If True (default), also delete the namespace that was
            created for this reference after removal.

    Returns:
        ActionResultModel dict with ``context.reference_node`` and
        ``context.namespace_removed``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return error_result(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist in the scene".format(reference_node),
            ).to_dict()

        if cmds.objectType(reference_node) != "reference":
            return error_result(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}', expected 'reference'".format(reference_node, cmds.objectType(reference_node)),
            ).to_dict()

        # Resolve namespace before removal
        namespace_removed = ""
        if remove_namespace:
            try:
                namespace_removed = cmds.referenceQuery(reference_node, namespace=True, shortName=True)
            except Exception:
                namespace_removed = ""

        cmds.file(referenceNode=reference_node, removeReference=True)

        # Remove the namespace if it still exists
        if remove_namespace and namespace_removed:
            try:
                if cmds.namespace(exists=namespace_removed):
                    cmds.namespace(removeNamespace=namespace_removed, mergeNamespaceWithRoot=True)
            except Exception:
                pass

        return success_result(
            "Removed reference '{}'".format(reference_node),
            reference_node=reference_node,
            namespace_removed=namespace_removed if remove_namespace else "",
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_reference failed")
        return error_result("Failed to remove reference '{}'".format(reference_node), str(exc)).to_dict()


def reload_reference(reference_node: str) -> dict:
    """Reload a previously unloaded (or modified) file reference.

    Args:
        reference_node: Name of the reference node to reload
            (e.g. ``"characterRN"``).  Use :func:`list_references` to
            discover reference nodes.

    Returns:
        ActionResultModel dict with ``context.reference_node``,
        ``context.file_path``, and ``context.loaded``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return error_result(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist".format(reference_node),
            ).to_dict()

        if cmds.objectType(reference_node) != "reference":
            return error_result(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}'".format(reference_node, cmds.objectType(reference_node)),
            ).to_dict()

        cmds.file(loadReference=reference_node)

        try:
            file_path = cmds.referenceQuery(reference_node, filename=True, withoutCopyNumber=True)
        except Exception:
            file_path = ""

        return success_result(
            "Reloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            file_path=file_path,
            loaded=True,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("reload_reference failed")
        return error_result("Failed to reload reference '{}'".format(reference_node), str(exc)).to_dict()


def unload_reference(reference_node: str) -> dict:
    """Unload a file reference without removing it from the scene.

    Unloading keeps the reference node intact but removes the referenced
    nodes from memory.  Use :func:`reload_reference` to restore them.

    Args:
        reference_node: Name of the reference node to unload.

    Returns:
        ActionResultModel dict with ``context.reference_node`` and
        ``context.loaded`` (``False`` after success).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return error_result(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist".format(reference_node),
            ).to_dict()

        if cmds.objectType(reference_node) != "reference":
            return error_result(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}'".format(reference_node, cmds.objectType(reference_node)),
            ).to_dict()

        cmds.file(unloadReference=reference_node)

        return success_result(
            "Unloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            loaded=False,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("unload_reference failed")
        return error_result("Failed to unload reference '{}'".format(reference_node), str(exc)).to_dict()


def list_namespaces(root_only: bool = False) -> dict:
    """List all namespaces in the current scene.

    Args:
        root_only: If True, return only top-level namespaces directly under
            the root (``":"``).  If False (default), list all namespaces
            recursively.

    Returns:
        ActionResultModel dict with ``context.namespaces`` — a list of
        namespace strings — and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if root_only:
            raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=False) or []
        else:
            raw = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []

        # Filter built-in namespaces
        built_in = {"UI", "shared"}
        namespaces = [ns for ns in raw if ns not in built_in]

        return success_result(
            "Found {} namespace(s)".format(len(namespaces)),
            namespaces=namespaces,
            count=len(namespaces),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_namespaces failed")
        return error_result("Failed to list namespaces", str(exc)).to_dict()
