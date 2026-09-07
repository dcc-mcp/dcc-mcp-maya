# Maya agent capability audit

Audit baseline: upstream `main` at `c6242647b7e07325a08cf5fc122989bbf16e1e95`
(2026-09-07, adapter 0.9.26). This is a domain-level gap register, not a claim
to implement every Maya command or every plugin API. Recheck runtime/plugin
versions and open issues before reusing the assessment.

## Evidence levels

- **Implemented**: a declared typed action and executable implementation exist.
- **Unit verified**: controlled tests establish specified behavior, not host behavior.
- **Host verified**: the exact host performed the operation and its result was read back.
- **Limited**: version, plugin, renderer, license, or format requirements apply.
- **Missing / unverified**: no supported typed path found, or acceptance is outstanding.

## Domain register

| Domain | Implemented surface | Gaps / next acceptance |
|---|---|---|
| Scene and object discovery | `maya-scene`: hierarchy, selection, type/pattern search, node references, transforms, bounds, cameras | Hierarchy result is unbounded; several failed field queries silently default. Verify duplicate leaf names, instances, references, and very large scenes. |
| Parameters and dependency graph | `maya-attributes` CRUD; `maya-node-graph` describe/create/connect/disconnect/history; `maya-cmds://` and `maya-api://` resource discovery | Attribute type/lock/connection constraints need per-type tests. Introspection or arbitrary execution is not typed command coverage. |
| Polygon / NURBS authoring | Primitives; loft/lathe, arrays, pivots, mirror, merge/separate/combine, cleanup, subdivision; freeze/history cleanup | #492 remains open. Typed extrude/bevel/inset/boolean/edge-loop actions are absent from the audited declarations. Re-run the modeling benchmark; historical raw-script percentages are not current results. |
| UVs | Create/delete/copy sets, projection/unfold/normalization, auto UV, UV and shell queries | Baseline UV queries used the wrong set/count and mutated the active set. PR #514 fixes count and shell readback with non-current/empty-set native tests. UDIM and multi-shape tests remain. |
| Materials and textures | Material create/assign/readback, attributes, shading group queries, presets | #495: no typed `assign_texture`, reload or repath. Bake code still defaults to mentalRay and does not establish Arnold bake output. File textures, colorspaces, UDIM and missing dependencies need assertions. |
| Animation | Batch keys, values/tangents readback, JSON curve import/export, timeline, bake | #493 partially implemented. Verify multi-object curves, weighted tangents and infinity round trips. Native bake calls are monolithic. |
| Rigging / skin | Joints/controls/constraints, IK, deformers, get/set skin weights, rig-state export, pose library | #493: no joint-chain batch action or general weight-file IO declared. Verify non-normalized weights, bind state, references and pose failure recovery. |
| Dynamics / Bifrost | Legacy rigid body/fields; typed Bifrost graph/node/port/property/connection operations | No typed Nucleus/nCloth/nParticle/cache status suite. Bifrost requires its plugin; graph edits do not establish successful evaluation or cache output. |
| Interchange | Generic import, FBX import/export, OBJ export, Alembic export; USD revision sync and native asset import | Generic USD plugin/type preparation missing at baseline (fixed in this batch). AssetDescriptor import lacks Alembic. SpeedTree geometry round trips passed in the combined source checkout; unit/axis and material fidelity gaps remain (below). |
| Rendering / capture | Frame/sequence render, settings, HDR Arnold setup, color management, viewport/playblast | #494 partially implemented. Typed AOV lifecycle/exposure and uniform-frame checks are not established. Arnold plugin and render license plus GUI/VP2 availability are separate gates. |
| Pipeline | Projects, metadata, publishing, shot export, assemblies, asset discovery, Deadline job submission/status | Validate external service availability, credentials, file artifacts and failure/partial-write states. Submission acknowledgement is not a rendered deliverable. |
| Jobs / cancellation | Core job persistence/status, adapter dispatchers and cancellation helper | `async` alone does not permit native-call interruption. Only a small subset of scripts checks cancellation. Test terminal status, inner failure, transport loss and no duplicate retry. Main-thread vs inline standalone dispatch needs real-host comparison. |
| Error recovery / lifecycle | Core envelopes, readiness, process sentinel, shutdown hooks, optional recovery-dialog detection, scene resources | A live registry row is not successful dispatch. Recovery must read back state; no blanket rollback or modal-dialog immunity is established. |
| Setup / discovery | Install/verify/uninstall and minimal skill loading; typed plugin lifecycle | #491 and #490 remain open. Verify a fresh installed host, package origin and search/load/describe/call; source-tree success does not prove release packaging. |

## Batch 1: interchange reliability

Generic import now prepares `mayaUsdPlugin` for `.usd`, `.usda`, `.usdc`,
selects the native translator, rejects directories before plugin loading,
and retains bounded node lists. FBX import is declared asynchronous with
a 300-second hint. No new tool count is used as a coverage metric.

Tests cover USD extensions/case, plugin load ordering, unavailable plugins,
directory rejection, existing FBX exports, and bounded import results.
Live validation uses Maya 2026 / Python 3.11 / installed Core 0.19.86,
with this checkout supplying the adapter. These versions deliberately differ
from local unit tests using Core 0.20.23; neither establishes other Maya years.

The CLI `search -> load-skill -> describe -> call --wait` smoke completed
USD/FBX/OBJ/Alembic imports on a manually drained `MayaUiDispatcher` in
Maya 2026 standalone (3/11/9/3 returned nodes respectively). The same FBX
fixture returned zero nodes through `MayaStandaloneDispatcher`; dedicated
FBX import also raised a boolean-flag error on `cmds.ls(long=True)` there.
This is a runtime dispatch gap, not evidence of successful FBX import on
the default inline path. GUI acceptance remains unverified. Tests include
native OBJ/USD mesh face/vertex readback.

## SpeedTree acceptance matrix

The producer handoff must include absolute source paths, hashes, export
settings, source dimensions/units/up axis, textures, expected meshes/materials,
LOD layout and wind/frame-range expectations. No source assets are checked in.

| Format | Maya dependency / route | Required readback | Boundary |
|---|---|---|---|
| FBX | `fbxmaya`; `import_fbx` for explicit import options | New nodes, hierarchy, bounds, UVs, SG membership, file texture paths, animation curves | Plugin import state matters. Do not infer runtime wind/LOD behavior from geometry. |
| OBJ | `objExport`; `import_file` | Mesh/polygon/UV counts, bounds; resolve MTL and texture paths | Accept geometry/material interchange separately from animation and procedural wind. |
| Alembic | `AbcImport`; `import_file` | Meshes, UVs, cache nodes, sampled frame changes, bounds | Cached motion requires time samples; shader reconstruction and interactive LOD behavior are separate. |
| USD | `mayaUsdPlugin`; native `import_file`, or revision sync proxy mode | Native meshes or explicit proxy stage, units/up axis, bindings, dependencies, authored time samples | Native conversion and stage composition have different fidelity/editability boundaries. |

Each import runs in a disposable scene. Wait for the core job's terminal state,
then inspect the inner tool result and run read-only checks. Preserve failures
and plugin versions. Save/reopen representative outputs before claiming
artifact acceptance. A synthetic mesh is a translator smoke, not SpeedTree
acceptance; an opened PR or green CI is not licensed GUI acceptance.

## Real SpeedTree acceptance (2026-09-07)

Validated a shared palm source export and all 157 manifest-listed files by
size and SHA-256. The producer used a Blender export preset; the manifest
labels all exports centimeters and enables Y/Z swap only for Alembic.
The combined PR #513/#514 source checkout was tested through typed CLI calls
in Maya 2026 with the manually pumped dispatcher described above.

All four formats produced one mesh, 6,081 vertices, 8,498 triangular faces,
and 6,109 UVs per set. Saved Maya ASCII scenes reopened with the same face
counts and declare centimeter units. This establishes geometry persistence,
not full material, coordinate, wind or LOD fidelity.

| Format | UV sets | XYZ bounds size (cm, rounded) | Material / dependency observations |
|---|---|---|---|
| FBX | `uv0`, `blend_ao` | 730.34, 1234.38, 752.98 | Six materials; 18 file nodes: 17 relative paths exist beside the export and one is empty. Maya/render path resolution remains unverified. |
| OBJ | `map1` | 23.96, 24.70, 40.50 | Six materials; six valid absolute color paths and six invalid paths equal to `1`. |
| Alembic | `map1` | 23.96, 24.70, 40.50 | Six shading groups all use one default shader; no file texture nodes. |
| USD (native) | `st` | 730.34, 1234.38, 752.98 | Six materials; all 23 file texture paths exist. Render appearance remains unverified. |

FBX/USD agree; OBJ/Alembic have a roughly 30.48 scale difference and exchanged
Y/Z extents compared with them. Do not automatically normalize without an
authoritative source dimension/up-axis contract. No animation-curve,
AlembicNode or lodGroup nodes were reported; bounds at frames 1 and 24 matched.
Those checks do not establish the absence of all animation or procedural wind.
A producer motion/LOD sample and expected frame range are still required.

Local affected unit/schema checks and four Maya 2026 native tests passed.
CI has not passed: observed failures include shared job-storage ownership
locks and the CLI installer's dcc-cua manifest rejection before skills lint.
These remain merge gates; source-host results do not establish packaged release
or GUI acceptance. Detailed manifests, CLI envelopes and saved scenes are kept
as local evidence, not committed source assets.

## Official references

- [Autodesk Maya command reference](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/index.html)
- [File import and returnNewNodes](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/file.html)
- [Plugin queries](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/pluginInfo.html)
- [UV query and uvSetName](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/polyEditUV.html)
- [Maya USD](https://github.com/Autodesk/maya-usd)
- [Core public contracts](https://github.com/dcc-mcp/dcc-mcp-core/blob/main/llms.txt)
- Open work: [#490](https://github.com/dcc-mcp/dcc-mcp-maya/issues/490), [#491](https://github.com/dcc-mcp/dcc-mcp-maya/issues/491), [#492](https://github.com/dcc-mcp/dcc-mcp-maya/issues/492), [#493](https://github.com/dcc-mcp/dcc-mcp-maya/issues/493), [#494](https://github.com/dcc-mcp/dcc-mcp-maya/issues/494), [#495](https://github.com/dcc-mcp/dcc-mcp-maya/issues/495).
