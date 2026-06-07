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

---

## maya2022-compat

> **Target audience:** agents running against Maya 2022 instances.
> All snippets below include version detection so the same code works across
> Maya 2022, 2023, 2024, and 2025 without modification.
>
> **Core pattern:** parse `cmds.about(version=True)`, compare major version,
> and branch on the flag set.  For full introspection of a command's flags
> at runtime, use `dcc_introspect__signature("maya.cmds.<cmd>")` first
> (see `references/INTROSPECTION.md`).

### maya2022-compat: version detection helper

```python
import maya.cmds as cmds

def maya_major_version() -> int:
    """Return the Maya major version as an integer (2022, 2023, ...)."""
    ver = cmds.about(version=True)  # e.g. "2022.3"
    try:
        return int(ver.split(".")[0])
    except (ValueError, IndexError):
        return 0
```

### maya2022-compat: polyReduce (no keepQuads flag)

The `keepQuads` / `keepQuadsWeight` flags were added in Maya 2023.
In Maya 2022, `polyReduce` does **not** accept these flags —
calling `cmds.polyReduce(keepQuads=True)` raises `RuntimeError`.

**Version-safe wrapper:**

```python
import maya.cmds as cmds

def safe_poly_reduce(mesh, percentage=50, keep_quads=True):
    """Apply polyReduce, skipping keepQuads on Maya 2022."""
    flags = {"percentage": percentage}
    if maya_major_version() >= 2023:
        flags["keepQuads"] = keep_quads
    return cmds.polyReduce(mesh, **flags)
```

### maya2022-compat: lattice (no localInfluence flag)

The `localInfluence` / `li` flag was added in Maya 2023.
In Maya 2022, `cmds.lattice(localInfluence=True)` raises `RuntimeError`.

**Version-safe wrapper:**

```python
import maya.cmds as cmds

def safe_lattice(objects, divisions=(2, 2, 2), local_influence=True):
    """Create a lattice deformer, skipping localInfluence on Maya 2022."""
    flags = {
        "divisions": divisions,
        "objectCentered": True,
    }
    if maya_major_version() >= 2023:
        flags["localInfluence"] = local_influence
    lattice_node, _ffd, _base = cmds.lattice(objects, **flags)
    return lattice_node
```

### maya2022-compat: joint orient version differences

`cmds.joint()` orient behavior changed across Maya versions:

| Version | Default `-oj` | Notes |
|---------|---------------|-------|
| 2022 | `"none"` | Must set `-oj xyz` explicitly for world-aligned joints |
| 2023+ | `"xyz"` | Default changed; `-oj` flag still accepted but default differs |

Orient mode strings accepted: `"xyz"`, `"yzx"`, `"zxy"`, `"xzy"`, `"yxz"`,
`"zyx"`, `"none"`.

**Version-safe wrapper:**

```python
import maya.cmds as cmds

def safe_joint(name=None, position=(0, 0, 0), orient="xyz"):
    """Create a joint with explicit orient, consistent across Maya versions.

    Always passes -oj explicitly instead of relying on the version-dependent
    default.  Maya 2022 defaults to 'none'; 2023+ defaults to 'xyz'.
    """
    flags = {
        "position": position,
        "orientation": orient,  # explicit: avoids version-dependent default
    }
    if name:
        flags["name"] = name
    return cmds.joint(**flags)
```

### maya2022-compat: arnoldRender (-camera, not -c)

In the **MtoA version bundled with Maya 2022** (`mtoa` 5.0.x), the
`arnoldRender` MEL command uses `-camera <name>` (long form).  The short
`-c` flag does **not** work and raises a MEL syntax error.

Later MtoA versions (5.2+, Maya 2023+) accept both `-c` and `-camera`.

**Version-safe wrapper:**

```python
import maya.cmds as cmds
import maya.mel as mel

def safe_arnold_render(camera="persp", width=1920, height=1080,
                       start_frame=None, end_frame=None):
    """Call arnoldRender with the correct camera flag for the Maya version.

    Uses -camera on MtoA < 5.2 (Maya 2022); uses -c on MtoA >= 5.2 or when
    available.  Also guards against headless/MEL-only render failures.
    """
    mtoa_ver = 0
    try:
        if cmds.pluginInfo("mtoa", q=True, loaded=True):
            ver_str = cmds.pluginInfo("mtoa", q=True, version=True) or "0"
            mtoa_ver = float(".".join(ver_str.split(".")[:2]))
    except Exception:
        pass

    # MtoA < 5.2 only accepts -camera; >= 5.2 accepts both
    if mtoa_ver > 0 and mtoa_ver < 5.2:
        cam_flag = "-camera"
    else:
        cam_flag = "-c"

    cmd = 'arnoldRender {} {} -x {} -y {}'.format(cam_flag, camera, width, height)
    if start_frame is not None and end_frame is not None:
        cmd += ' -s {} -e {}'.format(start_frame, end_frame)

    return mel.eval(cmd)
```

### maya2022-compat: aiSkyDomeLight.color (file node or RGB components)

`aiSkyDomeLight` (Arnold skydome light) exposes a `color` attribute, but
it is a **texturable color slot** — you cannot set it with a plain
`setAttr` + float3.  The attribute expects a connected **file texture
node** (for HDR/EXR maps) or must be driven via the per-channel
`colorR` / `colorG` / `colorB` child attributes.

This applies to **all** Maya versions with MtoA, not just 2022, but
agents trained on newer docs frequently hit this footgun.

**Method A — connect a file texture (for HDR/EXR environment lighting):**

```python
import maya.cmds as cmds

def set_skydome_texture(skydome_light, image_path):
    """Connect a file texture node to aiSkyDomeLight.color for HDR lighting."""
    # Create file node and load texture
    file_node = cmds.shadingNode("file", asTexture=True,
                                  name="{}_file".format(skydome_light))
    cmds.setAttr(file_node + ".fileTextureName", image_path, type="string")

    # Connect file.outColor → aiSkyDomeLight.color
    cmds.connectAttr(file_node + ".outColor",
                     skydome_light + ".color", force=True)
    return file_node
```

**Method B — set solid color via RGB components:**

```python
def set_skydome_solid_color(skydome_light, r=0.5, g=0.7, b=1.0):
    """Set aiSkyDomeLight solid color through per-channel attributes."""
    cmds.setAttr(skydome_light + ".colorR", r)
    cmds.setAttr(skydome_light + ".colorG", g)
    cmds.setAttr(skydome_light + ".colorB", b)
```

**Method C — create skydome light with texture in one step:**

```python
def create_skydome_with_hdri(image_path, intensity=1.0, name="skydomeLight"):
    """Create an aiSkyDomeLight pre-wired to an HDR file texture."""
    light_shape = cmds.shadingNode("aiSkyDomeLight", asLight=True,
                                    name=name + "Shape")
    light_xform = cmds.listRelatives(light_shape, parent=True, fullPath=True)[0]

    file_node = cmds.shadingNode("file", asTexture=True,
                                  name=light_xform + "_file")
    cmds.setAttr(file_node + ".fileTextureName", image_path, type="string")
    cmds.connectAttr(file_node + ".outColor",
                     light_shape + ".color", force=True)
    cmds.setAttr(light_shape + ".intensity", intensity)

    return light_xform
```

### maya2022-compat: MtoA version check helper

```python
def mtoa_version_tuple():
    """Return (major, minor) for the loaded MtoA plugin, or (0, 0)."""
    import maya.cmds as cmds
    try:
        if cmds.pluginInfo("mtoa", q=True, loaded=True):
            ver_str = cmds.pluginInfo("mtoa", q=True, version=True) or "0"
            parts = ver_str.split(".")[:2]
            return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except Exception:
        pass
    return (0, 0)
```

### maya2022-compat: full version-probe wrapper

Combine all version probes into one reusable function that an agent can
drop into any `execute_python` payload before using the Maya 2022-safe
wrappers above.

```python
import maya.cmds as cmds

def probe_maya2022_compat():
    """Return a dict describing the Maya / MtoA compatibility surface.

    Agents can call this once, then branch on `maya_major` or individual
    `flags.*` booleans before assembling their payload.

    Returns::

        {
            "maya_version": "2022.3",
            "maya_major": 2022,
            "mtoa_version": "5.0.2",
            "flags": {
                "polyReduce_keepQuads": false,
                "lattice_localInfluence": false,
                "joint_default_orient_xyz": false,
                "arnoldRender_short_c": false,
                "aiSkyDomeLight_color_rgb": true,
            }
        }
    """
    ver_str = cmds.about(version=True)
    major = int(ver_str.split(".")[0]) if ver_str else 0

    mtoa_str = "0"
    try:
        if cmds.pluginInfo("mtoa", q=True, loaded=True):
            mtoa_str = cmds.pluginInfo("mtoa", q=True, version=True) or "0"
    except Exception:
        pass

    mtoa_parts = mtoa_str.split(".")
    mtoa_major = int(mtoa_parts[0]) if mtoa_parts else 0
    mtoa_minor = int(mtoa_parts[1]) if len(mtoa_parts) > 1 else 0

    return {
        "maya_version": ver_str,
        "maya_major": major,
        "mtoa_version": mtoa_str,
        "flags": {
            "polyReduce_keepQuads": major >= 2023,
            "lattice_localInfluence": major >= 2023,
            "joint_default_orient_xyz": major >= 2023,
            "arnoldRender_short_c": mtoa_major > 5 or (mtoa_major == 5 and mtoa_minor >= 2),
            "aiSkyDomeLight_color_rgb": True,  # always true — colorR/G/B children exist
        },
    }
