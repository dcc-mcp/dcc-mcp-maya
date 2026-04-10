---
name: maya-material-library
description: "Maya material library — save, load, and manage reusable material presets stored as JSON or Maya files"
dcc: maya
version: "1.0.0"
tags: [maya, materials, library, shading, presets]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-material-library

Reusable material preset management for Maya. Saves shader networks to a JSON
library and restores them, enabling consistent look-dev across shots and assets.

## Scripts

- `save_material` — Serialize a material and its attributes to a JSON preset file
- `load_material` — Recreate a material from a JSON preset and assign it optionally
- `list_materials` — List all preset files in a material library directory
- `delete_material_preset` — Remove a material preset file from the library
