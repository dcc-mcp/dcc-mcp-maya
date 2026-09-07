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
| UVs | Create/delete/copy sets, projection/unfold/normalization, auto UV, UV and shell queries | `get_uv_info(uv_set=...)` does not target that set and counts coordinate scalars. Fix readback before accepting textured imports. Multi-set/empty-set and UDIM tests needed. |
| Materials and textures | Material create/assign/readback, attributes, shading group queries, presets | #495: no typed `assign_texture`, reload or repath. Bake code still defaults to mentalRay and does not establish Arnold bake output. File textures, colorspaces, UDIM and missing dependencies need assertions. |
| Animation | Batch keys, values/tangents readback, JSON curve import/export, timeline, bake | #493 partially implemented. Verify multi-object curves, weighted tangents and infinity round trips. Native bake calls are monolithic. |
| Rigging / skin | Joints/controls/constraints, IK, deformers, get/set skin weights, rig-state export, pose library | #493: no joint-chain batch action or general weight-file IO declared. Verify non-normalized weights, bind state, references and pose failure recovery. |
| Dynamics / Bifrost | Legacy rigid body/fields; typed Bifrost graph/node/port/property/connection operations | No typed Nucleus/nCloth/nParticle/cache status suite. Bifrost requires its plugin; graph edits do not establish successful evaluation or cache output. |
| Interchange | Generic import, FBX import/export, OBJ export, Alembic export; USD revision sync and native asset import | Generic USD plugin/type preparation missing at baseline (fixed in this batch). AssetDescriptor import lacks Alembic. Per-format dependency/unit/axis/material fidelity and SpeedTree inputs still require acceptance. |
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
the default inline path. GUI acceptance and SpeedTree producer assets remain
unverified. Tests include native OBJ/USD mesh face/vertex readback.

## SpeedTree acceptance matrix (pending producer handoff)

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

## Official references

- [Autodesk Maya command reference](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/index.html)
- [File import and returnNewNodes](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/file.html)
- [Plugin queries](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/pluginInfo.html)
- [UV query and uvSetName](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/polyEditUV.html)
- [Maya USD](https://github.com/Autodesk/maya-usd)
- [Core public contracts](https://github.com/dcc-mcp/dcc-mcp-core/blob/main/llms.txt)
- Open work: [#490](https://github.com/dcc-mcp/dcc-mcp-maya/issues/490), [#491](https://github.com/dcc-mcp/dcc-mcp-maya/issues/491), [#492](https://github.com/dcc-mcp/dcc-mcp-maya/issues/492), [#493](https://github.com/dcc-mcp/dcc-mcp-maya/issues/493), [#494](https://github.com/dcc-mcp/dcc-mcp-maya/issues/494), [#495](https://github.com/dcc-mcp/dcc-mcp-maya/issues/495).
