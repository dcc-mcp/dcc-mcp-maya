from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "src" / "dcc_mcp_maya"
DISALLOWED_LS_FLAGS = ("long=True", "materials=True")
REGRESSED_SCRIPTS = (
    RUNTIME_ROOT
    / "skills"
    / "maya-import-to-scene"
    / "scripts"
    / "import_to_scene.py",
    RUNTIME_ROOT / "skills" / "maya-geometry" / "scripts" / "import_fbx.py",
    RUNTIME_ROOT / "skills" / "maya-materials" / "scripts" / "list_materials.py",
)


def test_regressed_import_and_material_scripts_use_short_ls_flags() -> None:
    offenders = []
    for path in REGRESSED_SCRIPTS:
        text = path.read_text(encoding="utf-8")
        for flag in DISALLOWED_LS_FLAGS:
            if "cmds.ls(" in text and flag in text:
                offenders.append(f"{path.relative_to(RUNTIME_ROOT)}: {flag}")

    assert offenders == []
