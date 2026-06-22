from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "src" / "dcc_mcp_maya"
DISALLOWED_LS_FLAGS = ("long=True", "materials=True")


def test_runtime_scripts_use_maya_ls_short_boolean_flags() -> None:
    offenders: list[str] = []
    for path in RUNTIME_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for flag in DISALLOWED_LS_FLAGS:
            if f"cmds.ls(" in text and flag in text:
                offenders.append(f"{path.relative_to(RUNTIME_ROOT)}: {flag}")

    assert offenders == []
