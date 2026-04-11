---
name: maya-audio
<<<<<<< HEAD
description: "Maya audio and sound node management"
=======
description: "Maya audio — import audio files, set timeline audio, list and remove audio nodes"
>>>>>>> origin/main
dcc: maya
version: "1.0.0"
tags: [maya, audio, sound, timeline]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-audio

<<<<<<< HEAD
Maya audio skill. Provides actions for querying sound nodes in Maya.

## Scripts

- `list_audio` — List all sound nodes in the scene with their file path and timeline offset
=======
Maya audio skill. Provides actions for importing audio files into Maya, attaching
them to the timeline, and managing sound nodes.

## Scripts

- `import_audio` — Import an audio file and create a sound node
- `list_audio` — List all sound nodes in the scene
- `set_timeline_audio` — Set the active timeline audio node
- `remove_audio` — Delete a sound node from the scene
>>>>>>> origin/main
