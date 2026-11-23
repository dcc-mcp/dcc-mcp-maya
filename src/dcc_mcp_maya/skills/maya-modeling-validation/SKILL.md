---
name: maya-modeling-validation
description: >-
  Export normalized Maya modeling state and verify bounded modeling operations
  for cross-DCC acceptance. Use after typed mesh, pivot, cleanup, or UV edits
  and before export or reference review.
license: MIT
compatibility: "dcc-mcp-maya 0.9+, Maya 2022+, dcc-mcp-core 0.20.0+"
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: validation
    version: "1.0.0"
    tags: [maya, modeling, validation, model-state, reference-fit, topology, uv, materials]
    search-hint: "Maya modeling state validation topology UV materials hierarchy reference fit fixed view review operation readback"
    search-aliases: [modeling validation, geometry acceptance, mesh readback, reference driven modeling, cross-DCC modeling]
    intent: "Validate Maya modeling results with structured state exports and repeatable review evidence."
    preconditions:
      - type: software
        name: maya
        version: ">=2022"
      - type: scene_state
        predicate: has_open_scene
    side-effects:
      modifies: "align_reference when apply=true"
      creates: "capture_model_review may create a temporary render output"
      targets: [modeling_state, validation_report, review_evidence]
    produces: [model_state, operation_report, review_evidence]
    requires: []
    tools: tools.yaml
    groups: groups.yaml
---

# maya-modeling-validation

This skill is the acceptance layer for Maya polygon modeling. It exports the
versioned `dcc-mcp/model-state@1` document consumed by Core verification and
keeps Maya-specific evidence in additive fields such as native history
parameters and operation readback.

## Workflow

1. Run typed authoring tools from `maya-primitives`, `maya-mesh-ops`, and
   `maya-uv-ops`.
2. Call `export_model_state` on the modeled transforms.
3. Call `verify_modeling_operation` for the operation that needs explicit
   native parameter and postcondition evidence.
4. Use `align_reference` with `apply=false` to inspect a bounded proposal, then
   repeat it with `apply=true` when the proposal is accepted.
5. Call `capture_model_review` with a named camera and fixed frame for
   repeatable visual evidence.
6. Pass `context.state` to Core `validate_scene_vs_spec`.

Incomplete Maya queries are marked in `state.unavailable` and set
`state.partial=true`. Review and operation reports retain the failing query,
expected value, observed value, and actionable error details.

## Scripts

- `export_model_state.py` — normalized state and additive Maya evidence.
- `verify_modeling_operation.py` — native history, transform, topology, and UV
  postcondition checks.
- `align_reference.py` — bounded uniform fit and center alignment between two
  scene objects.
- `capture_model_review.py` — deterministic camera/frame review evidence using
  the existing Maya render path.
