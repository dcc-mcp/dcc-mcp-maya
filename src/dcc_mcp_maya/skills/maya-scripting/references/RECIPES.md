# Maya Scripting Recipes

Verified snippets for common Maya operations. Each section is self-contained —
grep on any anchor heading to get runnable code.

**Convention:** `[0]` on a creation result gives the transform node; `[-1]` gives
the shape/history node. All snippets verified against Maya 2024 and 2025.

> Use `dcc_introspect__signature("maya.cmds.<cmd>")` to check exact flag names
> for your Maya version before calling. See `references/INTROSPECTION.md`.

---

## primitives

```python
import maya.cmds as cmds

# polyCube — returns [transform, historyNode]
cube, _ = cmds.polyCube(w=2, h=1, d=1, sx=1, sy=1, sz=1, name="myCube")

# polySphere — radius + subdivisions
sphere, _ = cmds.polySphere(r=1.5, sx=20, sy=20, name="mySphere")

# polyPlane — width/height, subdivisions
plane, _ = cmds.polyPlane(w=10, h=10, sx=5, sy=5, name="myPlane")

# polyCylinder
cyl, _ = cmds.polyCylinder(r=1, h=3, sx=20, sy=1, sz=1, name="myCyl")

# polyCone
cone, _ = cmds.polyCone(r=1, h=2, sx=20, sy=1, name="myCone")

# Rename the transform after creation
cmds.rename(cube, "groundPlane")
```

---

## xform

```python
import maya.cmds as cmds

# Set world-space translation (absolute)
cmds.xform("myCube", worldSpace=True, translation=[1, 2, 3])

# Query world-space translation
pos = cmds.xform("myCube", q=True, worldSpace=True, translation=True)
# [1.0, 2.0, 3.0]

# Set rotation in object space (Euler, degrees)
cmds.xform("myCube", objectSpace=True, rotation=[0, 45, 0])

# Set uniform scale
cmds.xform("myCube", scale=[2, 2, 2])

# Freeze transforms (zero out translate/rotate, normalize scale to 1)
cmds.makeIdentity("myCube", apply=True, translate=True, rotate=True, scale=True)

# Move pivot to bounding box center
bbox = cmds.exactWorldBoundingBox("myCube")
cx = (bbox[0] + bbox[3]) / 2
cy = (bbox[1] + bbox[4]) / 2
cz = (bbox[2] + bbox[5]) / 2
cmds.xform("myCube", worldSpace=True, pivots=[cx, cy, cz])
```

---

## selection

```python
import maya.cmds as cmds

# Get current selection (short names)
sel = cmds.ls(sl=True)

# Get current selection (full DAG paths — avoids name collisions)
sel_long = cmds.ls(sl=True, long=True)

# Select by type
meshes = cmds.ls(type="mesh")
joints = cmds.ls(type="joint")

# Select all transforms with "geo" in name, long path
geo = cmds.ls("*geo*", type="transform", long=True)

# Component selection pitfall: ls(sl=True) returns component strings like "myCube.vtx[0]"
cmds.select("myCube.vtx[0:3]")
verts = cmds.ls(sl=True, flatten=True)  # flatten=True expands ranges

# Filter selection to only mesh transforms
def selected_meshes():
    return [t for t in cmds.ls(sl=True, long=True)
            if cmds.listRelatives(t, shapes=True, type="mesh")]
```

---

## hierarchy

```python
import maya.cmds as cmds

# Parent B under A
cmds.parent("myChild", "myParent")

# Un-parent to world
cmds.parent("myChild", world=True)

# List immediate children (transforms only, full paths)
children = cmds.listRelatives("myParent", children=True,
                               type="transform", fullPath=True) or []

# List all descendants
descendants = cmds.listRelatives("myParent", allDescendents=True,
                                  fullPath=True) or []

# Walk up to root
def get_root(node):
    parents = cmds.listRelatives(node, parent=True, fullPath=True)
    return get_root(parents[0]) if parents else node

# DAG vs dependency graph: listRelatives is DAG only.
# For dependency graph connections use listConnections (see attributes section).
```

---

## attributes

```python
import maya.cmds as cmds

# Get scalar attribute
tx = cmds.getAttr("myCube.translateX")

# Get float3 (returns list-of-tuple: [(x, y, z)])
translate = cmds.getAttr("myCube.translate")[0]  # (tx, ty, tz)

# Set scalar
cmds.setAttr("myCube.translateX", 5.0)

# Set float3
cmds.setAttr("myCube.translate", 1.0, 2.0, 3.0, type="double3")

# Set string attribute
cmds.setAttr("myNode.notes", "my note", type="string")

# Lock an attribute
cmds.setAttr("myCube.scaleX", lock=True)

# Add custom float attribute
cmds.addAttr("myCube", longName="myFloat", attributeType="float",
             defaultValue=0.0, keyable=True)

# Connect attributes (drive B with A)
cmds.connectAttr("myCube.translateX", "mySphere.translateX", force=True)

# List incoming connections to a node
conns = cmds.listConnections("myCube", source=True, destination=False,
                               plugs=True, connections=True) or []

# Query attribute type
attr_type = cmds.attributeQuery("translate", node="myCube", attributeType=True)
```

---

## namespaces

```python
import maya.cmds as cmds

# Create namespace
cmds.namespace(add="myRig")

# List all namespaces (excludes UI/system namespaces)
ns_list = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []

# Rename all nodes to use a new namespace prefix
def move_to_namespace(nodes, new_ns):
    cmds.namespace(add=new_ns, parent=":")
    for node in nodes:
        short = node.split(":")[-1]
        cmds.rename(node, "{}:{}".format(new_ns, short))

# Safe delete namespace (merge objects into root)
cmds.namespace(removeNamespace=":myRig", mergeNamespaceWithParent=True)
```

---

## references

```python
import maya.cmds as cmds

# Load a file reference
nodes = cmds.file(
    "/path/to/asset.ma",
    reference=True,
    namespace="charA",
    returnNewNodes=True,
)

# List all reference nodes
ref_nodes = cmds.ls(type="reference")

# Query reference file path from reference node
ref_path = cmds.referenceQuery("charARN", filename=True)

# Check if reference is loaded
is_loaded = cmds.referenceQuery("charARN", isLoaded=True)

# Unload reference (keep edits)
cmds.file(unloadReference="charARN")

# Remove reference (discard edits)
cmds.file(removeReference=True, referenceNode="charARN")

# Export selected objects as reference-ready file
cmds.file(
    "/path/to/export.ma",
    exportSelected=True,
    type="mayaAscii",
    preserveReferences=True,
)
```

---

## materials

```python
import maya.cmds as cmds

# Create Lambert material + shading engine
mat = cmds.shadingNode("lambert", asShader=True, name="myMat")
sg = cmds.sets(renderable=True, noSurfaceShader=True,
               empty=True, name="myMatSG")
cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader", force=True)

# Set color
cmds.setAttr(mat + ".color", 1.0, 0.2, 0.2, type="double3")

# Assign material to objects
cmds.sets("myCube", edit=True, forceElement=sg)

# Query which material is on an object
def get_material(obj):
    shapes = cmds.listRelatives(obj, shapes=True) or []
    for shape in shapes:
        sgs = cmds.listConnections(shape, type="shadingEngine") or []
        for sg in sgs:
            mats = cmds.listConnections(sg + ".surfaceShader") or []
            if mats:
                return mats[0]
    return None

# Create aiStandardSurface (Arnold) — same pattern
if cmds.pluginInfo("mtoa", q=True, loaded=True):
    ai_mat = cmds.shadingNode("aiStandardSurface", asShader=True)
    ai_sg  = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                       name=ai_mat + "SG")
    cmds.connectAttr(ai_mat + ".outColor", ai_sg + ".surfaceShader", force=True)
```

---

## rendering

```python
import maya.cmds as cmds

# Playblast to file
cmds.playblast(
    format="image",
    filename="/tmp/playblast",
    sequenceTime=False,
    clearCache=True,
    viewer=False,
    showOrnaments=False,
    percent=100,
    compression="png",
    widthHeight=[1920, 1080],
    startTime=1,
    endTime=24,
    forceOverwrite=True,
)

# Set render resolution
cmds.setAttr("defaultResolution.width", 1920)
cmds.setAttr("defaultResolution.height", 1080)
cmds.setAttr("defaultResolution.deviceAspectRatio", 1920 / 1080)

# Query current renderer
renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")

# Render current frame (batch-safe software render)
cmds.render(x=1920, y=1080)
```

---

## animation

```python
import maya.cmds as cmds

# Set keyframe on translateY at current time
cmds.setKeyframe("mySphere", attribute="translateY")

# Set keyframe at specific time and value
cmds.setKeyframe("mySphere", attribute="translateY", time=10, value=5.0)

# Query keyframe times on an attribute
times = cmds.keyframe("mySphere.translateY", q=True, timeChange=True) or []

# Query keyframe values
values = cmds.keyframe("mySphere.translateY", q=True, valueChange=True) or []

# Set tangent type (flat, auto, linear, spline, step)
cmds.keyTangent("mySphere.translateY", time=(10, 10),
                inTangentType="flat", outTangentType="flat")

# Bake simulation to keyframes
cmds.bakeSimulation(
    "mySphere",
    time=(1, 100),
    sampleBy=1,
    attribute=["translateX", "translateY", "translateZ"],
)

# Query time range of the scene
start = cmds.playbackOptions(q=True, minTime=True)
end   = cmds.playbackOptions(q=True, maxTime=True)
```

---

## openmaya

```python
# Use OpenMaya (maya.api) when you need performance, iterators, or
# data types not reachable via cmds (MMatrix, MDagPath, MFnMesh vertices).

import maya.api.OpenMaya as om

# Get MDagPath for a named node
sel = om.MSelectionList()
sel.add("myCube")
dag_path = sel.getDagPath(0)

# MFnTransform — read world matrix
fn_xform = om.MFnTransform(dag_path)
matrix = fn_xform.transformation().asMatrix()

# MFnMesh — iterate vertices
mesh_dag = sel.getDagPath(0)
fn_mesh = om.MFnMesh(mesh_dag)
pts = fn_mesh.getPoints(om.MSpace.kWorld)
for i, pt in enumerate(pts):
    print(i, pt.x, pt.y, pt.z)

# MFnDependencyNode — generic attribute access
sel2 = om.MSelectionList()
sel2.add("mySphere")
obj = sel2.getDependNode(0)
fn_dep = om.MFnDependencyNode(obj)
attr = fn_dep.attribute("translateX")
plug = om.MPlug(obj, attr)
print(plug.asFloat())

# When to drop to OpenMaya vs cmds:
# - Batch operations on thousands of components (MFnMesh, MItMeshVertex)
# - Reading/writing raw MMatrix / MVector without string serialisation
# - Writing Maya plugins or callbacks (MMessage, MPxCommand)
# cmds is fine for everything else.
```

---

## undo

```python
import maya.cmds as cmds

# Wrap a multi-step operation in a single undo chunk
cmds.undoInfo(openChunk=True, chunkName="myOperation")
try:
    cmds.polyCube(name="cube1")
    cmds.move(0, 2, 0)
    cmds.setAttr("cube1.scaleX", 3)
finally:
    cmds.undoInfo(closeChunk=True)

# Disable undo for performance-critical bulk ops (re-enable afterwards)
cmds.undoInfo(stateWithoutFlush=False)
try:
    for i in range(1000):
        cmds.spaceLocator(name="loc{}".format(i))
finally:
    cmds.undoInfo(stateWithoutFlush=True)
```

---

## threading

```python
# Maya's scene state (cmds, MFn*) must be accessed on the main thread.
# dcc-mcp-core enforces this via DeferredExecutor — tools with
# affinity: main are routed to the UI thread automatically.
#
# If you ever need to schedule work from a non-main thread yourself:

import maya.utils

def my_main_thread_work():
    import maya.cmds as cmds
    return cmds.ls(sl=True)

# executeDeferred queues the callable on the main thread (fire-and-forget)
maya.utils.executeDeferred(my_main_thread_work)

# executeInMainThreadWithResult blocks until the result is ready
result = maya.utils.executeInMainThreadWithResult(my_main_thread_work)

# Never call cmds.* directly from a Python threading.Thread — it will
# crash Maya or return corrupt data silently.
```

---

## errors

```python
# Common RuntimeError messages and what they mean:

# "No object matches name: <name>"
#   → Node does not exist or is in a namespace. Try cmds.ls("*:<name>").

# "Cannot parent an object under itself"
#   → Circular hierarchy. Check cmds.listRelatives chain.

# "The attribute '<attr>' is locked"
#   → cmds.setAttr(..., lock=False) first, or check reference lock.

# "Object '<name>' not found"  (from MSelectionList.add)
#   → Typo, wrong namespace, or node hasn't been created yet.

# "No renderer found" (from cmds.render)
#   → Render plugin not loaded: cmds.loadPlugin("Mayatomr") or "mtoa".

import maya.cmds as cmds

def safe_get_attr(node, attr, default=None):
    """Return attribute value or default if node/attr does not exist."""
    full = "{}.{}".format(node, attr)
    if cmds.objExists(full):
        return cmds.getAttr(full)
    return default

def safe_set_attr(node, attr, *value, **kwargs):
    """Set attribute only if it exists and is not locked."""
    full = "{}.{}".format(node, attr)
    if not cmds.objExists(full):
        return False
    if cmds.getAttr(full, lock=True):
        cmds.setAttr(full, lock=False)
    cmds.setAttr(full, *value, **kwargs)
    return True
```
