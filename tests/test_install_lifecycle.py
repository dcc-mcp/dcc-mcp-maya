"""Install SOP v1 contract tests for the Maya adapter."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _configure_fake_maya(install, tmp_path, monkeypatch, version="2025"):
    maya_root = tmp_path / ("Maya%s" % version)
    maya_root.mkdir(exist_ok=True)
    modules_dir = tmp_path / "maya-profile" / "modules"
    scripts_dir = tmp_path / "maya-profile" / "scripts"
    receipt = tmp_path / "receipts" / "maya.json"
    monkeypatch.setenv("DCC_MCP_MAYA_MODULES_DIR", str(modules_dir))
    monkeypatch.setenv("DCC_MCP_MAYA_SCRIPTS_DIR", str(scripts_dir))
    monkeypatch.setenv("DCC_MCP_MAYA_RECEIPT", str(receipt))
    monkeypatch.setattr(
        install,
        "_probe_target",
        lambda _python: {
            "maya_version": version,
            "python_version": "3.11.9",
            "core_version": "0.19.91",
            "adapter_version": install.__version__,
        },
    )
    return maya_root, modules_dir, scripts_dir, receipt


def test_install_dry_run_emits_a_complete_non_mutating_plan(tmp_path, monkeypatch, capsys):
    """The public CLI plans the exact Maya target without writing it."""
    from dcc_mcp_maya import install

    maya_root = tmp_path / "Maya2025"
    maya_root.mkdir()
    mayapy = Path(sys.executable)
    maya_modules = tmp_path / "maya" / "modules"
    receipt = tmp_path / "receipts" / "maya.json"
    monkeypatch.setenv("DCC_MCP_MAYA_VERSION", "2025")
    monkeypatch.setenv("DCC_MCP_MAYA_MODULES_DIR", str(maya_modules))
    monkeypatch.setenv("DCC_MCP_MAYA_RECEIPT", str(receipt))
    monkeypatch.setattr(
        install,
        "_probe_target",
        lambda _python: {
            "maya_version": "2025",
            "python_version": "3.11.9",
            "core_version": "0.19.91",
            "adapter_version": install.__version__,
        },
    )

    exit_code = install.main(
        [
            "install",
            "--json",
            "--dry-run",
            "--dcc-path",
            str(maya_root),
            "--python",
            str(mayapy),
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["schema_version"] == 1
    assert report["status"] == "planned"
    assert report["dcc_type"] == "maya"
    assert report["install_state"] == "fresh"
    assert report["host"]["version"] == "2025"
    assert report["python"]["path"] == str(mayapy.resolve())
    assert [step["id"] for step in report["steps"]] == [
        "preflight",
        "stage",
        "commit",
        "verify",
    ]
    assert "--yes" in report["next_steps"][0]["command"]
    assert not maya_modules.exists()
    assert not receipt.exists()


def test_package_exposes_the_standard_lifecycle_console_entrypoint():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[project.scripts]" in pyproject
    assert 'dcc-mcp-maya = "dcc_mcp_maya.install:main"' in pyproject


def test_receipt_round_trip_owns_module_descriptor_and_usersetup(tmp_path, monkeypatch, capsys):
    """A no-host install remains recoverable and never claims live usability."""
    from dcc_mcp_maya import install

    maya_root, modules_dir, scripts_dir, receipt_path = _configure_fake_maya(install, tmp_path, monkeypatch)
    user_setup = scripts_dir / "userSetup.py"
    user_setup.parent.mkdir(parents=True)
    original_user_setup = b"# artist startup\nARTIST_SETTING = True\n"
    user_setup.write_bytes(original_user_setup)
    monkeypatch.setattr(
        install,
        "wait_for_sidecar_ready",
        lambda *_args, **_kwargs: {"success": False, "status": "unavailable"},
    )
    common = ["--json", "--dcc-path", str(maya_root), "--python", sys.executable]

    assert install.main(["install", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    installed = json.loads(capsys.readouterr().out)
    module_root = modules_dir / "dcc-mcp-maya"
    descriptor = modules_dir / "dcc_mcp_maya.mod"
    assert installed["status"] == "partial"
    assert installed["verify"]["directly_usable"] is False
    assert installed["verify"]["failure_stage"] == "readiness"
    assert installed["verify"]["failure_reason"] == "sidecar_unavailable"
    assert installed["verify"]["probe_tool"] == "host.ping"
    assert (module_root / "python" / "dcc_mcp_maya" / "__init__.py").is_file()
    assert (module_root / "plug-ins" / "dcc_mcp_maya_plugin.py").is_file()
    assert (module_root / "scripts" / "userSetup.py").is_file()
    assert descriptor.is_file()
    assert install.USER_SETUP_BEGIN in user_setup.read_text(encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert {entry["kind"] for entry in receipt["artifacts"]} == {"tree", "file", "user_setup"}
    assert receipt["python"]["path"] == str(Path(sys.executable).resolve())

    assert install.main(["install", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    assert user_setup.read_text(encoding="utf-8").count(install.USER_SETUP_BEGIN) == 1
    assert not list(tmp_path.rglob("*.stage-*"))
    assert not list(tmp_path.rglob("*.backup-*"))

    assert install.main(["uninstall", "--yes", *common]) == install.INSTALL_EXIT_OK
    removed = json.loads(capsys.readouterr().out)
    assert removed["status"] == "ok"
    assert not module_root.exists()
    assert not descriptor.exists()
    assert user_setup.read_bytes() == original_user_setup
    assert not receipt_path.exists()

    assert install.main(["uninstall", "--yes", *common]) == install.INSTALL_EXIT_OK
    assert json.loads(capsys.readouterr().out)["steps"][0]["status"] == "already_absent"


def test_typed_host_ping_is_required_for_direct_usability(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, _modules, _scripts, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    probes = []

    def ready(registry_dir=None, **kwargs):
        probes.append((registry_dir, kwargs))
        return {"success": True, "status": "ready", "instance_id": "maya-1"}

    monkeypatch.setattr(install, "wait_for_sidecar_ready", ready)

    assert (
        install.main(["install", "--yes", "--json", "--dcc-path", str(maya_root), "--python", sys.executable])
        == install.INSTALL_EXIT_OK
    )
    report = json.loads(capsys.readouterr().out)
    assert report["verify"]["directly_usable"] is True
    assert probes[0][1]["dcc_type"] == "maya"
    assert probes[0][1]["probe_tool"] == "host.ping"
    assert probes[0][1]["timeout_secs"] == 10.0


def test_receipt_commit_failure_rolls_back_all_previous_artifacts(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, modules_dir, scripts_dir, receipt_path = _configure_fake_maya(install, tmp_path, monkeypatch)
    monkeypatch.setattr(install, "wait_for_sidecar_ready", lambda *_args, **_kwargs: {"success": False})
    common = ["--json", "--dcc-path", str(maya_root), "--python", sys.executable]
    assert install.main(["install", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    module_root = modules_dir / "dcc-mcp-maya"
    descriptor = modules_dir / "dcc_mcp_maya.mod"
    user_setup = scripts_dir / "userSetup.py"
    before = {
        "module": install._tree_sha256(module_root),
        "descriptor": descriptor.read_bytes(),
        "user_setup": user_setup.read_bytes(),
        "receipt": receipt_path.read_bytes(),
    }
    real_replace = install._replace_path

    def fail_receipt(source, destination):
        if destination == receipt_path and ".stage-" in source.name:
            raise OSError("simulated receipt commit failure")
        return real_replace(source, destination)

    monkeypatch.setattr(install, "_replace_path", fail_receipt)
    assert install.main(["upgrade", "--yes", *common]) == install.INSTALL_EXIT_INSTALL
    failed = json.loads(capsys.readouterr().out)
    assert failed["verify"]["failure_reason"] == "commit_failed"
    assert install._tree_sha256(module_root) == before["module"]
    assert descriptor.read_bytes() == before["descriptor"]
    assert user_setup.read_bytes() == before["user_setup"]
    assert receipt_path.read_bytes() == before["receipt"]
    assert not list(tmp_path.rglob("*.stage-*"))
    assert not list(tmp_path.rglob("*.backup-*"))


def test_windows_lock_is_reported_as_requires_restart(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, _modules, _scripts, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    monkeypatch.setattr(
        install,
        "_install_transaction",
        lambda _ctx: (_ for _ in ()).throw(PermissionError("locked native module")),
    )
    monkeypatch.setattr(install, "_is_windows_lock", lambda _exc: True)

    assert (
        install.main(["install", "--yes", "--json", "--dcc-path", str(maya_root), "--python", sys.executable])
        == install.INSTALL_EXIT_REQUIRES_RESTART
    )
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "requires_restart"
    assert report["verify"]["failure_reason"] == "windows_file_lock"


def test_preflight_rejects_unsupported_maya_and_core_before_writes(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root = tmp_path / "Maya"
    maya_root.mkdir()
    monkeypatch.setenv("DCC_MCP_MAYA_MODULES_DIR", str(tmp_path / "modules"))
    monkeypatch.setattr(
        install,
        "_probe_target",
        lambda _python: {
            "maya_version": "2019",
            "python_version": "2.7",
            "core_version": "0.19.44",
            "adapter_version": install.__version__,
        },
    )
    assert (
        install.main(["install", "--dry-run", "--json", "--dcc-path", str(maya_root), "--python", sys.executable])
        == install.INSTALL_EXIT_PREFLIGHT
    )
    report = json.loads(capsys.readouterr().out)
    assert report["verify"]["failure_reason"] == "unsupported_maya_version"
    assert not (tmp_path / "modules").exists()

    monkeypatch.setattr(
        install,
        "_probe_target",
        lambda _python: {
            "maya_version": "2027",
            "python_version": "3.11",
            "core_version": "0.19.44",
            "adapter_version": install.__version__,
        },
    )
    assert (
        install.main(["install", "--dry-run", "--json", "--dcc-path", str(maya_root), "--python", sys.executable])
        == install.INSTALL_EXIT_PREFLIGHT
    )
    assert json.loads(capsys.readouterr().out)["verify"]["failure_reason"] == "core_version_unsupported"

    for unsupported_core in ("1.0", "1.0.0"):
        monkeypatch.setattr(
            install,
            "_probe_target",
            lambda _python, version=unsupported_core: {
                "maya_version": "2027",
                "python_version": "3.11",
                "core_version": version,
                "adapter_version": install.__version__,
            },
        )
        assert (
            install.main(["install", "--dry-run", "--json", "--dcc-path", str(maya_root), "--python", sys.executable])
            == install.INSTALL_EXIT_PREFLIGHT
        )
        assert json.loads(capsys.readouterr().out)["verify"]["failure_reason"] == "core_version_unsupported"

    monkeypatch.setattr(
        install,
        "_probe_target",
        lambda _python: {
            "maya_version": "2020",
            "python_version": "2.7.18",
            "core_version": "0.19.91",
            "adapter_version": install.__version__,
        },
    )
    assert (
        install.main(["install", "--dry-run", "--json", "--dcc-path", str(maya_root), "--python", sys.executable])
        == install.INSTALL_EXIT_PREFLIGHT
    )
    assert json.loads(capsys.readouterr().out)["verify"]["failure_reason"] == "unsupported_python_version"


@pytest.mark.parametrize(
    ("core_version", "expected_exit"),
    (
        ("garbage 0.19.45", 10),
        ("0.19.45garbage", 10),
        ("0..19.45", 10),
        ("", 10),
        ("0.19.44", 10),
        ("1.0.0rc1", 10),
        ("1.0.0.dev1", 10),
        ("1.0.0", 10),
        ("0.19.45", 0),
        ("0.19.45.0", 0),
        ("0.19.45+local", 0),
        ("0.19.91", 0),
    ),
)
def test_operator_dry_run_strictly_validates_complete_core_version_before_writes(
    core_version, expected_exit, tmp_path, monkeypatch, capsys
):
    from dcc_mcp_maya import install

    maya_root = tmp_path / "Maya2025"
    maya_root.mkdir()
    modules_dir = tmp_path / "profile" / "modules"
    scripts_dir = tmp_path / "profile" / "scripts"
    receipt = tmp_path / "receipts" / "maya.json"
    monkeypatch.setenv("DCC_MCP_MAYA_MODULES_DIR", str(modules_dir))
    monkeypatch.setenv("DCC_MCP_MAYA_SCRIPTS_DIR", str(scripts_dir))
    monkeypatch.setenv("DCC_MCP_MAYA_RECEIPT", str(receipt))
    monkeypatch.setattr(
        install,
        "_probe_target",
        lambda _python: {
            "maya_version": "2025",
            "python_version": "3.11.9",
            "core_version": core_version,
            "adapter_version": install.__version__,
        },
    )

    exit_code = install.main(
        ["install", "--dry-run", "--json", "--dcc-path", str(maya_root), "--python", sys.executable]
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == expected_exit
    assert report["status"] == ("planned" if expected_exit == 0 else "failed")
    assert not modules_dir.exists()
    assert not scripts_dir.exists()
    assert not receipt.exists()


def test_public_reports_use_shared_schema_and_stable_exit_codes():
    from dcc_mcp_maya import install

    schema = install.load_install_sop_schema()
    assert schema["$id"] == "https://dcc-mcp.github.io/schemas/adapter-install-sop-v1.schema.json"
    assert install.INSTALL_EXIT_CODES == {
        "ok": 0,
        "preflight": 10,
        "acquire": 20,
        "install": 30,
        "verify": 40,
        "requires_restart": 50,
    }


def test_install_runbook_covers_the_complete_owning_repo_contract():
    guide = (ROOT / "install.md").read_text(encoding="utf-8")

    for heading in (
        "## Requirements",
        "## Supported versions",
        "## Agent quick path",
        "## Manual path",
        "## Verify",
        "## Upgrade",
        "## Uninstall",
        "## Troubleshooting",
    ):
        assert heading in guide
    for platform in ("Windows", "macOS", "Linux"):
        assert platform in guide
    for verb in ("install", "status", "verify", "uninstall", "upgrade"):
        assert "dcc-mcp-maya %s" % verb in guide
    for flag in ("--json", "--yes", "--dry-run", "--dcc-path", "--python"):
        assert flag in guide
    for term in (
        "receipt",
        "rollback",
        "capture_bootstrap_errors",
        "host.ping",
        "https://raw.githubusercontent.com/dcc-mcp/dcc-mcp-maya/main/install.md",
    ):
        assert term in guide


def test_released_wheel_contains_the_plugin_and_usersetup_install_assets():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"maya/plugin/dcc_mcp_maya_plugin.py" = "dcc_mcp_maya/install_assets/maya/plugin/dcc_mcp_maya_plugin.py"'
        in pyproject
    )
    assert '"maya/userSetup.py" = "dcc_mcp_maya/install_assets/maya/userSetup.py"' in pyproject


def test_packaged_usersetup_delegates_to_captured_bounded_bootstrap():
    source = (ROOT / "maya" / "userSetup.py").read_text(encoding="utf-8")

    assert "from dcc_mcp_maya.install import bootstrap_user_setup" in source
    assert "capture_bootstrap_errors" in (ROOT / "src" / "dcc_mcp_maya" / "install.py").read_text(encoding="utf-8")
    assert "lowestPriority=True" in source


def test_module_zip_payload_is_bounded_receipted_and_installed(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, modules_dir, _scripts, receipt_path = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "dcc-mcp-maya.zip"
    with zipfile.ZipFile(str(payload), "w") as archive:
        archive.writestr("dcc-mcp-maya/python/dcc_mcp_maya/__init__.py", "ZIP_PAYLOAD = True\n")
        archive.writestr("dcc-mcp-maya/python37/dcc_mcp_core/_core.pyd", b"native-cp37")
        archive.writestr("dcc-mcp-maya/plug-ins/dcc_mcp_maya_plugin.py", "# plugin\n")
        archive.writestr("dcc-mcp-maya/scripts/userSetup.py", "# setup\n")
        archive.writestr("dcc-mcp-maya/dcc_mcp_maya.mod", "+ placeholder\n")
        archive.writestr(
            "dcc-mcp-maya/module-info.json",
            json.dumps(
                {
                    "name": "dcc_mcp_maya",
                    "adapter_version": install.__version__,
                    "min_core_version": install.MIN_CORE_VERSION,
                    "max_core_version_exclusive": install.MAX_CORE_VERSION,
                }
            ),
        )
    monkeypatch.setattr(install, "wait_for_sidecar_ready", lambda *_args, **_kwargs: {"success": False})

    assert (
        install.main(
            [
                "install",
                "--yes",
                "--json",
                "--dcc-path",
                str(maya_root),
                "--python",
                sys.executable,
                "--module-zip",
                str(payload),
            ]
        )
        == install.INSTALL_EXIT_VERIFY
    )
    capsys.readouterr()
    assert "ZIP_PAYLOAD = True" in (modules_dir / "dcc-mcp-maya" / "python" / "dcc_mcp_maya" / "__init__.py").read_text(
        encoding="utf-8"
    )
    descriptor_lines = (modules_dir / "dcc_mcp_maya.mod").read_text(encoding="utf-8").splitlines()
    maya_2022 = next(index for index, line in enumerate(descriptor_lines) if "MAYAVERSION:2022" in line)
    maya_2023 = next(index for index, line in enumerate(descriptor_lines) if "MAYAVERSION:2023" in line)
    assert descriptor_lines[maya_2022 + 1] == "PYTHONPATH+:=python37"
    assert descriptor_lines[maya_2023 + 1] == "PYTHONPATH+:=python"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["source"] == {
        "kind": "module_zip",
        "path": str(payload.resolve()),
        "sha256": install._sha256(payload),
    }


def test_module_zip_rejects_path_traversal_before_profile_writes(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, modules_dir, _scripts, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(str(payload), "w") as archive:
        archive.writestr("../escape.py", "owned = True\n")

    assert (
        install.main(
            [
                "install",
                "--yes",
                "--json",
                "--dcc-path",
                str(maya_root),
                "--python",
                sys.executable,
                "--module-zip",
                str(payload),
            ]
        )
        == install.INSTALL_EXIT_ACQUIRE
    )
    report = json.loads(capsys.readouterr().out)
    assert report["verify"]["failure_reason"] == "unsafe_module_zip"
    assert not modules_dir.exists()


@pytest.mark.parametrize(
    "metadata_patch",
    (
        {},
        {"min_core_version": "0.19.44", "max_core_version_exclusive": "1.0.0"},
        {"min_core_version": "0.19.45", "max_core_version_exclusive": "1.0"},
    ),
)
def test_module_zip_rejects_missing_or_mismatched_core_bounds_before_writes(
    metadata_patch, tmp_path, monkeypatch, capsys
):
    from dcc_mcp_maya import install

    maya_root, modules_dir, scripts_dir, receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "contract-drift.zip"
    metadata = {"name": "dcc_mcp_maya", "adapter_version": install.__version__}
    metadata.update(metadata_patch)
    with zipfile.ZipFile(str(payload), "w") as archive:
        archive.writestr("dcc-mcp-maya/python/dcc_mcp_maya/__init__.py", "")
        archive.writestr("dcc-mcp-maya/plug-ins/dcc_mcp_maya_plugin.py", "")
        archive.writestr("dcc-mcp-maya/scripts/userSetup.py", "")
        archive.writestr("dcc-mcp-maya/module-info.json", json.dumps(metadata))

    exit_code = install.main(
        [
            "install",
            "--yes",
            "--json",
            "--dcc-path",
            str(maya_root),
            "--python",
            sys.executable,
            "--module-zip",
            str(payload),
        ]
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == install.INSTALL_EXIT_ACQUIRE
    assert report["verify"]["failure_reason"] == "module_zip_core_contract_mismatch"
    assert not modules_dir.exists()
    assert not scripts_dir.exists()
    assert not receipt.exists()
    assert not (tmp_path / "escape.py").exists()


def test_module_zip_rejects_adapter_version_drift_before_writes(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, modules_dir, _scripts, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "stale.zip"
    with zipfile.ZipFile(str(payload), "w") as archive:
        archive.writestr("dcc-mcp-maya/python/dcc_mcp_maya/__init__.py", "")
        archive.writestr("dcc-mcp-maya/plug-ins/dcc_mcp_maya_plugin.py", "")
        archive.writestr("dcc-mcp-maya/scripts/userSetup.py", "")
        archive.writestr(
            "dcc-mcp-maya/module-info.json",
            json.dumps({"name": "dcc_mcp_maya", "adapter_version": "0.0.1"}),
        )

    assert (
        install.main(
            [
                "install",
                "--yes",
                "--json",
                "--dcc-path",
                str(maya_root),
                "--python",
                sys.executable,
                "--module-zip",
                str(payload),
            ]
        )
        == install.INSTALL_EXIT_ACQUIRE
    )
    report = json.loads(capsys.readouterr().out)
    assert report["verify"]["failure_reason"] == "module_zip_version_mismatch"
    assert not modules_dir.exists()


def test_uninstall_preserves_artist_edits_made_after_install(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, _modules, scripts_dir, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    monkeypatch.setattr(install, "wait_for_sidecar_ready", lambda *_args, **_kwargs: {"success": False})
    common = ["--json", "--dcc-path", str(maya_root), "--python", sys.executable]
    assert install.main(["install", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    user_setup = scripts_dir / "userSetup.py"
    user_setup.write_text(user_setup.read_text(encoding="utf-8") + "ARTIST_AFTER_INSTALL = True\n", encoding="utf-8")

    assert install.main(["uninstall", "--yes", *common]) == install.INSTALL_EXIT_OK
    capsys.readouterr()
    restored = user_setup.read_text(encoding="utf-8")
    assert "ARTIST_AFTER_INSTALL = True" in restored
    assert install.USER_SETUP_BEGIN not in restored


def test_uninstall_preserves_preexisting_and_later_usersetup_edits(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, _modules, scripts_dir, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    user_setup = scripts_dir / "userSetup.py"
    user_setup.parent.mkdir(parents=True)
    user_setup.write_text("ARTIST_BEFORE = True\n", encoding="utf-8")
    monkeypatch.setattr(install, "wait_for_sidecar_ready", lambda *_args, **_kwargs: {"success": False})
    common = ["--json", "--dcc-path", str(maya_root), "--python", sys.executable]
    assert install.main(["install", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    user_setup.write_text(user_setup.read_text(encoding="utf-8") + "ARTIST_AFTER = True\n", encoding="utf-8")

    assert install.main(["uninstall", "--yes", *common]) == install.INSTALL_EXIT_OK
    capsys.readouterr()
    restored = user_setup.read_text(encoding="utf-8")
    assert "ARTIST_BEFORE = True" in restored
    assert "ARTIST_AFTER = True" in restored
    assert install.USER_SETUP_BEGIN not in restored


def test_upgrade_refreshes_usersetup_baseline_before_uninstall(tmp_path, monkeypatch, capsys):
    """An upgrade must not discard unmanaged edits made after the first install."""
    from dcc_mcp_maya import install

    maya_root, _modules, scripts_dir, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    user_setup = scripts_dir / "userSetup.py"
    user_setup.parent.mkdir(parents=True)
    user_setup.write_text("ARTIST_BEFORE = True\n", encoding="utf-8")
    monkeypatch.setattr(install, "wait_for_sidecar_ready", lambda *_args, **_kwargs: {"success": False})
    common = ["--json", "--dcc-path", str(maya_root), "--python", sys.executable]

    assert install.main(["install", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    user_setup.write_text(user_setup.read_text(encoding="utf-8") + "ARTIST_BETWEEN = True\n", encoding="utf-8")

    assert install.main(["upgrade", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    assert install.main(["uninstall", "--yes", *common]) == install.INSTALL_EXIT_OK
    capsys.readouterr()

    restored = user_setup.read_text(encoding="utf-8")
    assert "ARTIST_BEFORE = True" in restored
    assert "ARTIST_BETWEEN = True" in restored
    assert install.USER_SETUP_BEGIN not in restored


@pytest.mark.parametrize(
    "collision_entry",
    [
        "dcc-mcp-maya/python/dcc_mcp_maya/__init__.py",
        "dcc-mcp-maya/PYTHON/dcc_mcp_maya/__init__.py",
        "dcc-mcp-maya/python/dcc_mcp_maya",
    ],
    ids=["duplicate", "windows-casefold", "file-directory-prefix"],
)
def test_module_zip_rejects_canonical_path_collisions_before_writes(collision_entry, tmp_path, monkeypatch, capsys):
    """Every ZIP member must map to one unambiguous destination on Windows."""
    from dcc_mcp_maya import install

    maya_root, modules_dir, _scripts, _receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "colliding.zip"
    with zipfile.ZipFile(str(payload), "w") as archive:
        archive.writestr("dcc-mcp-maya/python/dcc_mcp_maya/__init__.py", "TRUSTED = True\n")
        archive.writestr("dcc-mcp-maya/plug-ins/dcc_mcp_maya_plugin.py", "# plugin\n")
        archive.writestr("dcc-mcp-maya/scripts/userSetup.py", "# setup\n")
        archive.writestr(
            "dcc-mcp-maya/module-info.json",
            json.dumps({"name": "dcc_mcp_maya", "adapter_version": install.__version__}),
        )
        archive.writestr(collision_entry, "UNTRUSTED = True\n")

    assert (
        install.main(
            [
                "install",
                "--yes",
                "--json",
                "--dcc-path",
                str(maya_root),
                "--python",
                sys.executable,
                "--module-zip",
                str(payload),
            ]
        )
        == install.INSTALL_EXIT_ACQUIRE
    )
    report = json.loads(capsys.readouterr().out)
    assert report["verify"]["failure_reason"] == "module_zip_path_collision"
    assert not modules_dir.exists()


def test_ci_has_an_explicit_lifecycle_round_trip_smoke():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "Install lifecycle smoke" in workflow
    assert "tests/test_install_lifecycle.py" in workflow


def test_preflight_discovers_supported_host_and_embedded_mayapy(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root = tmp_path / "Autodesk" / "Maya2027"
    mayapy = maya_root / "bin" / ("mayapy.exe" if sys.platform == "win32" else "mayapy")
    mayapy.parent.mkdir(parents=True)
    mayapy.write_bytes(b"")
    monkeypatch.setattr(install, "_candidate_host_paths", lambda _environ: iter([maya_root]))
    monkeypatch.setattr(
        install,
        "_probe_target",
        lambda selected: {
            "maya_version": "2027",
            "python_version": "3.11",
            "core_version": "0.19.91",
            "adapter_version": install.__version__,
            "selected": str(selected),
        },
    )
    monkeypatch.setenv("DCC_MCP_MAYA_MODULES_DIR", str(tmp_path / "profile" / "modules"))
    monkeypatch.setenv("DCC_MCP_MAYA_RECEIPT", str(tmp_path / "receipt.json"))

    assert install.main(["install", "--dry-run", "--json"]) == install.INSTALL_EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["host"]["path"] == str(maya_root.resolve())
    assert report["python"]["path"] == str(mayapy.resolve())
    assert report["python"]["selection_source"] == "discovered"
