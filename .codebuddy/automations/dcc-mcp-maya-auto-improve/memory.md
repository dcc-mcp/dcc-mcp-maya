# dcc-mcp-maya auto-improve execution memory

## 2026-04-08 (Round 1 — baseline)

### State before this round
- Branch: `auto-improve` (worktree at `G:/PycharmProjects/github/dcc-mcp-maya-auto-improve`)
- Version: 0.3.0
- Actions: 30 registered (scene×7, primitives×6, materials×4, animation×5, render×4, scripting×2)
- Tests: 142 passing, coverage 98%
- Uncovered: primitives.py lines 70, 108, 247→249; server.py lines 34, 104-105, 120-121, 127-128

### Work done
1. Rebased `auto-improve` onto remote `main` (4 commits rebased cleanly, origin/main was at `fe2897c`)
2. Added 3 new scene hierarchy Actions to `scene.py`:
   - `group_objects(objects, group_name=None, world=False)` — group objects under a new Maya group node
   - `parent_object(child, parent=None, world=False)` — set or clear object parent/world
   - `select_by_type(object_type)` — select all objects of a given Maya type
3. Registered all 3 new actions in `actions/__init__.py` → total 33 actions
4. Added 21 new tests in `test_actions_extended.py`:
   - `TestGroupObjects` (7 tests)
   - `TestParentObject` (7 tests)
   - `TestSelectByType` (4 tests)
   - `test_create_cube_with_name`, `test_create_cylinder_with_name`, `test_delete_objects_none_existing` (3 tests)
5. Updated `TestRegisterAllUpdated` to assert `len(actions) >= 24`

### State after this round
- Tests: 163 passing (all pass), 0 failures
- Coverage: 99% total (all action modules 100%, server.py 91%)
- Committed: `ed2010c feat(skills): add group_objects, parent_object, select_by_type scene hierarchy actions`
- Pushed: `origin/auto-improve` updated (force-with-lease after rebase)

### Remaining gaps for next round
- `server.py` lines 34, 104-105, 120-121, 127-128, 230 — only coverable with real Maya runtime
- Missing actions to consider:
  - `lock_object` / `unlock_object` — lock/unlock transform attributes
  - `duplicate_object` — duplicate with optional instance
  - `freeze_transforms` — apply transforms to shape
  - `center_pivot` — center object pivot point
  - `get_bounding_box` — query world-space bounding box
  - `set_visibility` — show/hide objects
  - `get_scene_info` (detailed) — full DAG hierarchy query
