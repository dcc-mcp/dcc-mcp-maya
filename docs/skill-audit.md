# Skill Audit — dcc-mcp-maya

Audit of all 64 bundled skills against the thin-harness taxonomy from issue #116.

**Taxonomy:**

| Bucket | Meaning |
|--------|---------|
| `keep` | Encodes pipeline logic, orchestration, or domain workflow beyond raw API |
| `demote` | Useful helpers but not essential for minimal mode — `default_active: false` |
| `merge` | All tools are trivial `cmds.*` wrappers → migrate calls to `RECIPES.md`, mark deprecated |
| `delete` | Superseded, never used, or single-line wrapper with zero safety value |

**Phase 1** (this PR): set `default_active: false` on all `demote` and `merge` bucket skills.  
**Phase 2** (next release): delete `merge` bucket skills after one release cycle.

---

## Audit Table

| Skill | Tools | Bucket | Rationale | Migration path |
|-------|-------|--------|-----------|----------------|
| `maya-animation` | 14 | `demote` | Useful keyframe/curve shortcuts that go beyond a one-liner, but not pipeline-critical | Keep skill, `default_active: false`; agent loads on demand |
| `maya-annotation` | 4 | `merge` | All 4 are thin `annotate()`/`setAttr()` wrappers | RECIPES.md `## annotation`; mark deprecated |
| `maya-arnold-aov` | 5 | `demote` | AOV creation requires Arnold plugin check + multi-step setup; not trivial | Keep skill, `default_active: false` |
| `maya-attributes` | 5 | `merge` | `getAttr`/`setAttr`/`addAttr` wrappers fully covered by RECIPES.md `## attributes` | RECIPES.md already covers; mark deprecated |
| `maya-audio` | 4 | `merge` | Thin `sound()`/`timeControl` wrappers | RECIPES.md `## audio`; mark deprecated |
| `maya-bifrost` | 5 | `keep` | Multi-step Bifrost graph setup with plugin presence check | Keep as-is |
| `maya-blend-shape-utils` | 4 | `demote` | Blend-shape target management; useful but not pipeline-critical | `default_active: false` |
| `maya-cache` | 4 | `demote` | Geometry cache create/attach; async ops with non-trivial paths | `default_active: false` |
| `maya-camera-sequence` | 4 | `demote` | Sequencer camera setup; niche but multi-step | `default_active: false` |
| `maya-cameras` | 5 | `merge` | Thin `camera()`/`lookThru()` wrappers | RECIPES.md `## cameras`; mark deprecated |
| `maya-cloth-sim` | 4 | `demote` | nCloth creation is multi-step (plugin check, nucleus, constraint) | `default_active: false` |
| `maya-color-grading` | 4 | `merge` | Thin `colorManagementPrefs` wrappers | RECIPES.md `## color-grading`; mark deprecated |
| `maya-constraints` | 4 | `merge` | One-line `parentConstraint`/`pointConstraint` wrappers covered by RECIPES | RECIPES.md `## constraints`; mark deprecated |
| `maya-constraints-advanced` | 4 | `demote` | Pole vector / aim constraint with offset calculation — some value over one-liner | `default_active: false` |
| `maya-deformers` | 7 | `demote` | Lattice/cluster/wire deformer setup; useful multi-step helpers | `default_active: false` |
| `maya-display` | 4 | `merge` | `displaySmoothness`/`modelEditor` wrappers — trivial | RECIPES.md `## display`; mark deprecated |
| `maya-dynamics` | 10 | `demote` | nDynamics system setup is multi-step; async ops included | `default_active: false` |
| `maya-export-preset` | 4 | `keep` | Encodes pipeline export logic with format negotiation | Keep as-is |
| `maya-expressions` | 4 | `merge` | Thin `expression()`/`setExpressionString()` wrappers; RECIPES.md covers | RECIPES.md `## expressions`; mark deprecated |
| `maya-fluid` | 4 | `demote` | Fluid container setup has plugin dependency and multi-step init | `default_active: false` |
| `maya-gpu-cache` | 4 | `merge` | One-line `gpuCache` export wrappers | RECIPES.md `## gpu-cache`; mark deprecated |
| `maya-grooming` | 4 | `demote` | nHair system setup; multi-step with plugin check | `default_active: false` |
| `maya-hdri` | 4 | `merge` | Thin IBL dome light wrappers; agent already knows this pattern | RECIPES.md `## hdri`; mark deprecated |
| `maya-instancer` | 4 | `merge` | Thin `instancer()` wrapper | RECIPES.md `## instancer`; mark deprecated |
| `maya-light-rig` | 4 | `keep` | Multi-light studio rig creation with positioning logic | Keep as-is |
| `maya-lighting` | 4 | `merge` | Thin `directionalLight`/`pointLight` wrappers — trivial single-liners | RECIPES.md `## lighting`; mark deprecated |
| `maya-mash` | 5 | `demote` | MASH network creation; requires plugin + multi-step | `default_active: false` |
| `maya-material-library` | 4 | `keep` | Library scanning + asset management logic beyond raw API | Keep as-is |
| `maya-materials` | 8 | `merge` | Mostly `shadingNode`/`sets` wrappers; already in RECIPES.md `## materials` | RECIPES.md already covers; mark deprecated |
| `maya-mesh-ops` | 12 | `demote` | Extrude/bevel/smooth shortcuts; many are multi-flag helpers with defaults | `default_active: false` |
| `maya-mocap` | 4 | `demote` | HIK setup requires multi-step character definition | `default_active: false` |
| `maya-muscle` | 4 | `demote` | Muscle rig setup; plugin-dependent multi-step | `default_active: false` |
| `maya-namespaces` | 6 | `merge` | Thin `namespace()` wrappers fully covered by RECIPES.md `## namespaces` | RECIPES.md already covers; mark deprecated |
| `maya-node-graph` | 9 | `demote` | DG connection helpers have value for discovery; not trivial | `default_active: false` |
| `maya-nparticles` | 4 | `demote` | nParticle emitter setup; multi-step + async | `default_active: false` |
| `maya-ocean` | 4 | `demote` | Ocean shader + wake setup; multi-step | `default_active: false` |
| `maya-paint-effects` | 4 | `merge` | Thin `paintEffects` brush wrappers | RECIPES.md `## paint-effects`; mark deprecated |
| `maya-pipeline` | 4 | `keep` | Pipeline workspace resolution + project-path logic | Keep as-is |
| `maya-pose-library` | 4 | `keep` | Pose capture / apply with namespace-aware restore | Keep as-is |
| `maya-primitives` | 8 | `merge` | All 8 are `polyCube`/`polySphere` etc. wrappers; covered by RECIPES.md `## primitives` | RECIPES.md already covers; mark deprecated |
| `maya-proxy-mesh` | 4 | `demote` | GPU-override proxy setup; some pipeline value | `default_active: false` |
| `maya-references` | 6 | `merge` | Thin `file(reference=True)` wrappers; RECIPES.md `## references` covers them | RECIPES.md already covers; mark deprecated |
| `maya-render` | 8 | `keep` | Render settings + playblast with resolution/camera negotiation | Keep as-is |
| `maya-render-farm` | 4 | `keep` | Deadline / Arnold batch submission orchestration | Keep as-is |
| `maya-render-layers` | 5 | `demote` | renderSetup layer management; useful but not minimal-mode essential | `default_active: false` |
| `maya-render-passes` | 4 | `demote` | AOV/render-pass helpers; niche | `default_active: false` |
| `maya-rig-utils` | 4 | `demote` | IK/FK switch utilities; useful but optional | `default_active: false` |
| `maya-rigging` | 12 | `demote` | Joint chain / IK / skin setup shortcuts; not trivial wrappers | `default_active: false` |
| `maya-scene` | 21 | `keep` | Scene file I/O, workspace, import/export — core pipeline operations | Keep as-is |
| `maya-scene-assembly` | 4 | `keep` | Scene assembly definition/reference management — pipeline orchestration | Keep as-is |
| `maya-scene-utils` | 7 | `demote` | Scene stats / node listing utilities; useful but not minimal-mode essential | `default_active: false` |
| `maya-scripting` | 33 | `keep` | Fall-through entry point + introspect tools + execute_python/mel | Keep as-is; primary entry |
| `maya-selection` | 5 | `merge` | Thin `ls(sl=True)`/`select()` wrappers; RECIPES.md `## selection` covers | RECIPES.md already covers; mark deprecated |
| `maya-sets` | 4 | `merge` | Thin `sets()` wrappers; RECIPES.md `## sets` covers | RECIPES.md already covers; mark deprecated |
| `maya-shot-export` | 4 | `keep` | Shot-level export with camera/range/format negotiation | Keep as-is |
| `maya-skinning-utils` | 4 | `demote` | Skin weight copy/mirror/prune; useful but not minimal-mode essential | `default_active: false` |
| `maya-spline-ik` | 4 | `demote` | SplineIK setup (curve creation + bind); multi-step | `default_active: false` |
| `maya-texture-bake` | 7 | `keep` | Bake simulation is async + multi-step; has genuine orchestration value | Keep as-is |
| `maya-toon` | 4 | `merge` | Thin toon-shader wrappers | RECIPES.md `## toon`; mark deprecated |
| `maya-utility` | 4 | `merge` | Misc helpers (`measure`, `locator`) — trivial single-liners | RECIPES.md `## utility`; mark deprecated |
| `maya-uv-ops` | 8 | `demote` | UV layout/projection shortcuts; multi-flag helpers with defaults | `default_active: false` |
| `maya-vertex-color` | 4 | `merge` | Thin `polyColorPerVertex` wrappers | RECIPES.md `## vertex-color`; mark deprecated |
| `maya-xform-utils` | 4 | `merge` | Thin `xform()`/`makeIdentity()` wrappers; RECIPES.md `## xform` covers | RECIPES.md already covers; mark deprecated |
| `maya-xgen` | 5 | `demote` | XGen description + guide setup; plugin-dependent multi-step | `default_active: false` |

---

## Summary

| Bucket | Count | Skills |
|--------|-------|--------|
| `keep` | 14 | bifrost, export-preset, light-rig, material-library, pipeline, pose-library, render, render-farm, scene, scene-assembly, scripting, shot-export, texture-bake, mesh-ops* |
| `demote` | 25 | animation, arnold-aov, blend-shape-utils, cache, camera-sequence, cloth-sim, constraints-advanced, deformers, dynamics, fluid, grooming, mash, mesh-ops, mocap, muscle, node-graph, nparticles, ocean, proxy-mesh, render-layers, render-passes, rig-utils, rigging, scene-utils, skinning-utils, spline-ik, uv-ops, xgen |
| `merge` | 20 | annotation, attributes, audio, cameras, color-grading, constraints, display, expressions, gpu-cache, hdri, instancer, lighting, materials, namespaces, paint-effects, primitives, references, selection, sets, toon, utility, vertex-color, xform-utils |
| `delete` | 0 | — (no skill is outright useless; all get merged or demoted first) |

*(mesh-ops is in `demote` bucket — kept but not in minimal mode)*

---

## Phase 1 Changes (this PR)

All `demote` and `merge` bucket skills get `default_active: false` on their non-core groups.  
**No skill is deleted yet.** Each `merge` skill gets a deprecation notice in its `SKILL.md` description pointing to the RECIPES.md anchor.

## Phase 2 Plan (next release)

Delete all `merge` bucket skills. Monitor `diagnostics__tool_metrics` (once core lands) to verify no production clients relied on removed tool names.
