# Interchange I/O checklist (Maya)

Use this with `skill_refs__read` / `recipes__get` — keep entries short and actionable.

## Before export (FBX / OBJ)

1. Prefer an **absolute** destination path; ensure the **parent directory exists** (create it outside Maya or use a host temp helper).
2. If the user cares about file naming on disk, ensure the Maya scene has been **saved or renamed** (`maya_geometry__save_scene` uses `file -rename` then save — use it instead of raw `file -save` on untitled scenes).
3. Run **`maya_geometry__file_exists`** only for *inputs* you are about to import — for export, rely on the tool result (`size_bytes`) after the call.

## Before import (FBX)

1. Source file **must exist** on disk; expand env vars / `~` in paths before calling.
2. Load **`fbxmaya`** is handled inside the tool; if the plugin is missing, the error envelope explains it.
3. Use a **`namespace`** when importing multiple FBX files into one scene to avoid name clashes.

## Gateway agents

1. **`load_skill("maya-geometry")`** in minimal mode before calling `maya_geometry__*`.
2. **`describe_tool`** on the concrete slug before the first call — schemas carry path semantics.
