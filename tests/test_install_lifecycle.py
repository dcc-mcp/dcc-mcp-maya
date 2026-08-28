"""Install SOP v1 contract tests for the Maya adapter."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _provenance_record(path, content):
    return {"path": path, "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}


def _write_provenanced_module_zip(install, payload, *, mutate=None, python37_content=None, extra_entries=None):
    core_path = "python/dcc_mcp_core/__init__.py"
    core_content = b'__version__ = "0.19.45"\n'
    metadata_path = "python/dcc_mcp_core-0.19.45.dist-info/METADATA"
    metadata_content = b"Metadata-Version: 2.1\nName: dcc-mcp-core\nVersion: 0.19.45\n"
    provenance = {
        "schema_version": 1,
        "name": "dcc-mcp-core",
        "version": install.MIN_CORE_VERSION,
        "source_wheels": [{"filename": "dcc_mcp_core-0.19.45-cp38-abi3-win_amd64.whl", "sha256": "a" * 64}],
        "roots": {
            "python": {
                "metadata": _provenance_record(metadata_path, metadata_content),
                "files": [_provenance_record(core_path, core_content)],
            }
        },
    }
    entries = {
        "python/dcc_mcp_maya/__init__.py": b"",
        core_path: core_content,
        metadata_path: metadata_content,
        "plug-ins/dcc_mcp_maya_plugin.py": b"",
        "scripts/userSetup.py": b"",
    }
    if python37_content is not None:
        python37_path = "python37/dcc_mcp_core/_core.pyd"
        python37_metadata_path = "python37/dcc_mcp_core-0.19.45.dist-info/METADATA"
        entries[python37_path] = python37_content
        entries[python37_metadata_path] = metadata_content
        provenance["roots"]["python37"] = {
            "metadata": _provenance_record(python37_metadata_path, metadata_content),
            "files": [_provenance_record(python37_path, python37_content)],
        }
    if extra_entries:
        entries.update(extra_entries)
    if mutate is not None:
        mutate(entries, provenance)
    provenance_content = (json.dumps(provenance, sort_keys=True) + "\n").encode()
    entries["core-provenance.json"] = provenance_content
    entries["module-info.json"] = json.dumps(
        {
            "name": "dcc_mcp_maya",
            "adapter_version": install.__version__,
            "embedded_core_version": install.MIN_CORE_VERSION,
            "min_core_version": install.MIN_CORE_VERSION,
            "max_core_version_exclusive": install.MAX_CORE_VERSION,
            "has_python37": python37_content is not None,
            "core_provenance": {
                "path": "core-provenance.json",
                "sha256": hashlib.sha256(provenance_content).hexdigest(),
            },
        }
    ).encode()
    with zipfile.ZipFile(str(payload), "w") as archive:
        for path, content in entries.items():
            archive.writestr("dcc-mcp-maya/" + path, content)
    return entries, provenance


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

    def fail_receipt(source, destination, publication_contract=None):
        if destination == receipt_path and ".stage-" in source.name:
            raise OSError("simulated receipt commit failure")
        return real_replace(source, destination, publication_contract)

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


def test_install_commit_boundary_positive_control_matches_receipt(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, modules_dir, scripts_dir, receipt_path = _configure_fake_maya(install, tmp_path, monkeypatch)
    monkeypatch.setattr(install, "wait_for_sidecar_ready", lambda *_args, **_kwargs: {"success": False})
    common = ["--json", "--dcc-path", str(maya_root), "--python", sys.executable]

    assert install.main(["install", "--yes", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    actual = {
        "tree": install._tree_sha256(modules_dir / "dcc-mcp-maya"),
        "file": install._sha256(modules_dir / "dcc_mcp_maya.mod"),
        "user_setup": install._sha256(scripts_dir / "userSetup.py"),
    }
    assert {entry["kind"]: entry["sha256"] for entry in receipt["artifacts"]} == actual


@pytest.mark.parametrize("drift", ["same_object_bytes", "same_path_new_object", "same_bytes_new_object"])
def test_install_commit_boundary_drift_rolls_back_before_receipt_publish(drift, tmp_path, monkeypatch, capsys):
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
    drifted = False

    def drift_at_module_publish(source, destination, publication_contract=None):
        nonlocal drifted
        if not drifted and destination == module_root and ".stage-" in source.name:
            target = source / "python" / "dcc_mcp_maya" / "__init__.py"
            content = b"MALICIOUS_COMMIT_BOUNDARY_REPLACEMENT = True\n"
            if drift == "same_object_bytes":
                target.write_bytes(content)
            elif drift == "same_path_new_object":
                replacement = target.with_name("replacement.py")
                replacement.write_bytes(content)
                replacement.replace(target)
            else:
                replacement = target.with_name("replacement.py")
                replacement.write_bytes(target.read_bytes())
                replacement.replace(target)
            drifted = True
        return real_replace(source, destination, publication_contract)

    monkeypatch.setattr(install, "_replace_path", drift_at_module_publish)
    assert install.main(["upgrade", "--yes", *common]) == install.INSTALL_EXIT_INSTALL
    failed = json.loads(capsys.readouterr().out)
    assert failed["verify"]["failure_reason"] == "stage_publication_mismatch"
    assert drifted
    assert install._tree_sha256(module_root) == before["module"]
    assert descriptor.read_bytes() == before["descriptor"]
    assert user_setup.read_bytes() == before["user_setup"]
    assert receipt_path.read_bytes() == before["receipt"]
    assert not list(tmp_path.rglob("*.stage-*"))
    assert not list(tmp_path.rglob("*.backup-*"))


def test_install_adoption_seam_same_bytes_new_object_rolls_back(tmp_path, monkeypatch, capsys):
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
    real_os_replace = install.os.replace
    drifted = False

    def swap_inside_adoption(source, destination):
        nonlocal drifted
        source_path = Path(source)
        destination_path = Path(destination)
        if not drifted and destination_path == module_root and ".stage-" in source_path.name:
            target = source_path / "python" / "dcc_mcp_maya" / "__init__.py"
            replacement = target.with_name("replacement.py")
            replacement.write_bytes(target.read_bytes())
            real_os_replace(str(replacement), str(target))
            drifted = True
        return real_os_replace(source, destination)

    monkeypatch.setattr(install.os, "replace", swap_inside_adoption)
    assert install.main(["upgrade", "--yes", *common]) == install.INSTALL_EXIT_INSTALL
    failed = json.loads(capsys.readouterr().out)
    assert failed["verify"]["failure_reason"] == "stage_publication_mismatch"
    assert drifted
    assert install._tree_sha256(module_root) == before["module"]
    assert descriptor.read_bytes() == before["descriptor"]
    assert user_setup.read_bytes() == before["user_setup"]
    assert receipt_path.read_bytes() == before["receipt"]
    assert not list(tmp_path.rglob("*.stage-*"))
    assert not list(tmp_path.rglob("*.backup-*"))


@pytest.mark.parametrize("artifact", ["module", "descriptor", "user_setup", "receipt"])
@pytest.mark.parametrize("mutation", ["external_hardlink", "same_bytes_new_object", "unchanged"])
def test_install_adoption_owns_each_published_artifact(artifact, mutation, tmp_path, monkeypatch, capsys):
    """Real adoption must reject aliases without losing prior state or foreign bytes."""
    from dcc_mcp_maya import install

    maya_root, modules_dir, scripts_dir, receipt_path = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "module.zip"
    _write_provenanced_module_zip(install, payload, python37_content=b"native-cp37")
    monkeypatch.setattr(install, "wait_for_sidecar_ready", lambda *_args, **_kwargs: {"success": False})
    common = ["--yes", "--json", "--dcc-path", str(maya_root), "--python", sys.executable, "--module-zip", str(payload)]
    assert install.main(["install", *common]) == install.INSTALL_EXIT_VERIFY
    capsys.readouterr()
    destinations = {
        "module": modules_dir / "dcc-mcp-maya",
        "descriptor": modules_dir / "dcc_mcp_maya.mod",
        "user_setup": scripts_dir / "userSetup.py",
        "receipt": receipt_path,
    }

    def installed_bytes():
        files = [item for item in destinations["module"].rglob("*") if item.is_file()]
        files.extend(destinations[name] for name in ("descriptor", "user_setup", "receipt"))
        return {item.relative_to(tmp_path).as_posix(): item.read_bytes() for item in files}

    prior = installed_bytes()
    real_replace = os.replace
    alias = tmp_path / "foreign-alias"
    adopted_bytes = []

    def inject_at_real_adoption(source, destination):
        source_path = Path(source)
        if not adopted_bytes and Path(destination) == destinations[artifact] and ".stage-" in source_path.name:
            target = source_path / "python/dcc_mcp_core/__init__.py" if artifact == "module" else source_path
            adopted_bytes.append(target.read_bytes())
            if mutation == "external_hardlink":
                os.link(str(target), str(alias))
            elif mutation == "same_bytes_new_object":
                replacement = tmp_path / "same-byte-replacement"
                replacement.write_bytes(adopted_bytes[0])
                real_replace(str(replacement), str(target))
        return real_replace(source, destination)

    monkeypatch.setattr(install.os, "replace", inject_at_real_adoption)
    exit_code = install.main(["upgrade", *common])
    report = json.loads(capsys.readouterr().out)
    assert adopted_bytes, "the actual adoption boundary must be exercised"
    if mutation == "unchanged":
        assert exit_code == install.INSTALL_EXIT_VERIFY
        assert report["verify"]["failure_reason"] == "sidecar_unavailable"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for entry in receipt["artifacts"]:
            path = Path(entry["path"])
            actual = install._tree_sha256(path) if entry["kind"] == "tree" else install._sha256(path)
            assert actual == entry["sha256"]
    else:
        assert exit_code == install.INSTALL_EXIT_INSTALL
        assert report["verify"]["failure_reason"] == "stage_publication_mismatch"
        assert installed_bytes() == prior
        if mutation == "external_hardlink":
            assert alias.read_bytes() == adopted_bytes[0]
            assert alias.stat().st_nlink == 1
            alias.write_bytes(b"external owner writes after rollback\n")
            assert installed_bytes() == prior
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
    _write_provenanced_module_zip(
        install,
        payload,
        python37_content=b"native-cp37",
        extra_entries={
            "python/dcc_mcp_maya/__init__.py": b"ZIP_PAYLOAD = True\n",
            "plug-ins/dcc_mcp_maya_plugin.py": b"# plugin\n",
            "scripts/userSetup.py": b"# setup\n",
            "dcc_mcp_maya.mod": b"+ placeholder\n",
        },
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


@pytest.mark.parametrize("embedded_core_version", (None, "0.19.44", "1.0", "1.0.0"))
def test_module_zip_rejects_invalid_embedded_core_version_before_writes(
    embedded_core_version, tmp_path, monkeypatch, capsys
):
    from dcc_mcp_maya import install

    maya_root, modules_dir, scripts_dir, receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "embedded-core-drift.zip"
    metadata = {
        "name": "dcc_mcp_maya",
        "adapter_version": install.__version__,
        "min_core_version": install.MIN_CORE_VERSION,
        "max_core_version_exclusive": install.MAX_CORE_VERSION,
    }
    if embedded_core_version is not None:
        metadata["embedded_core_version"] = embedded_core_version
    payload_version = embedded_core_version or install.MIN_CORE_VERSION
    with zipfile.ZipFile(str(payload), "w") as archive:
        archive.writestr("dcc-mcp-maya/python/dcc_mcp_maya/__init__.py", "")
        archive.writestr("dcc-mcp-maya/plug-ins/dcc_mcp_maya_plugin.py", "")
        archive.writestr("dcc-mcp-maya/scripts/userSetup.py", "")
        archive.writestr("dcc-mcp-maya/module-info.json", json.dumps(metadata))
        archive.writestr(
            "dcc-mcp-maya/python/dcc_mcp_core-%s.dist-info/METADATA" % payload_version,
            "Metadata-Version: 2.1\nName: dcc-mcp-core\nVersion: %s\n" % payload_version,
        )

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
    assert report["verify"]["failure_reason"] == "module_zip_embedded_core_invalid"
    assert not modules_dir.exists()
    assert not scripts_dir.exists()
    assert not receipt.exists()


def test_module_zip_rejects_embedded_core_payload_version_mismatch_before_writes(tmp_path, monkeypatch, capsys):
    from dcc_mcp_maya import install

    maya_root, modules_dir, scripts_dir, receipt = _configure_fake_maya(install, tmp_path, monkeypatch)
    payload = tmp_path / "embedded-core-payload-mismatch.zip"
    metadata = {
        "name": "dcc_mcp_maya",
        "adapter_version": install.__version__,
        "min_core_version": install.MIN_CORE_VERSION,
        "max_core_version_exclusive": install.MAX_CORE_VERSION,
        "embedded_core_version": install.MIN_CORE_VERSION,
    }
    with zipfile.ZipFile(str(payload), "w") as archive:
        archive.writestr("dcc-mcp-maya/python/dcc_mcp_maya/__init__.py", "")
        archive.writestr("dcc-mcp-maya/plug-ins/dcc_mcp_maya_plugin.py", "")
        archive.writestr("dcc-mcp-maya/scripts/userSetup.py", "")
        archive.writestr("dcc-mcp-maya/module-info.json", json.dumps(metadata))
        archive.writestr(
            "dcc-mcp-maya/python/dcc_mcp_core-0.19.46.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: dcc-mcp-core\nVersion: 0.19.46\n",
        )

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
    assert report["verify"]["failure_reason"] == "module_zip_embedded_core_mismatch"
    assert not modules_dir.exists()
    assert not scripts_dir.exists()
    assert not receipt.exists()


def test_module_zip_rejects_duplicate_same_version_core_identity_before_writes(tmp_path):
    from dcc_mcp_maya import install

    payload = tmp_path / "duplicate-core-identity.zip"

    def duplicate(entries, _provenance):
        entries["vendor/dcc_mcp_core-copy.dist-info/METADATA"] = (
            b"Metadata-Version: 2.1\nName: dcc_mcp_core\nVersion: 0.19.45\n"
        )

    _write_provenanced_module_zip(install, payload, mutate=duplicate)

    with pytest.raises(install.LifecycleError) as caught:
        install._validate_module_zip(payload)
    assert caught.value.reason == "module_zip_core_provenance_mismatch"


@pytest.mark.parametrize("root_name", ("python", "python37"))
def test_module_zip_rejects_conflicting_core_metadata_headers_per_root(root_name, tmp_path):
    from dcc_mcp_maya import install

    payload = tmp_path / ("conflicting-core-metadata-%s.zip" % root_name)

    def conflicting_headers(entries, provenance):
        metadata_path = "%s/dcc_mcp_core-0.19.45.dist-info/METADATA" % root_name
        metadata_content = (
            b"Metadata-Version: 2.1\nName: dcc-mcp-core\nName: attacker-core\nVersion: 0.19.45\nVersion: 9.9.9\n"
        )
        entries[metadata_path] = metadata_content
        provenance["roots"][root_name]["metadata"] = _provenance_record(metadata_path, metadata_content)

    _write_provenanced_module_zip(
        install,
        payload,
        mutate=conflicting_headers,
        python37_content=b"native-cp37" if root_name == "python37" else None,
    )

    with pytest.raises(install.LifecycleError) as caught:
        install._validate_module_zip(payload)
    assert caught.value.reason == "module_zip_core_provenance_mismatch"


@pytest.mark.parametrize("drift", ("same_path_new_object", "same_object_bytes"))
def test_module_zip_extraction_rejects_source_drift_after_validation(drift, tmp_path, monkeypatch):
    from dcc_mcp_maya import install

    payload = tmp_path / "module.zip"
    replacement = tmp_path / "replacement.zip"
    _write_provenanced_module_zip(install, payload)
    _write_provenanced_module_zip(
        install,
        replacement,
        extra_entries={"python/dcc_mcp_maya/__init__.py": b"MALICIOUS_REPLACEMENT = True\n"},
    )
    replacement_bytes = replacement.read_bytes()
    original_validate = install._validate_module_zip

    def validate_then_drift(path):
        result = original_validate(path)
        if drift == "same_path_new_object":
            replacement.replace(path)
        else:
            path.write_bytes(replacement_bytes)
        return result

    monkeypatch.setattr(install, "_validate_module_zip", validate_then_drift)
    stage = tmp_path / "stage"

    with pytest.raises(install.LifecycleError):
        install._extract_module_zip(payload, stage)
    assert not stage.exists() or not any(stage.rglob("*"))


def test_module_zip_rejects_hardlinked_source_before_validation(tmp_path):
    from dcc_mcp_maya import install

    original = tmp_path / "original.zip"
    payload = tmp_path / "hardlinked.zip"
    _write_provenanced_module_zip(install, original)
    os.link(original, payload)

    with pytest.raises(install.LifecycleError) as caught:
        install._validate_module_zip(payload)
    assert caught.value.reason == "unsafe_module_zip_source"


def test_module_zip_rejects_reparse_source_before_validation(tmp_path, monkeypatch):
    from dcc_mcp_maya import install

    payload = tmp_path / "reparse.zip"
    _write_provenanced_module_zip(install, payload)
    original_lstat = Path.lstat

    class ReparseStat:
        def __init__(self, stat_result):
            self._stat_result = stat_result
            self.st_file_attributes = getattr(stat_result, "st_file_attributes", 0) | 0x400

        def __getattr__(self, name):
            return getattr(self._stat_result, name)

    def reparse_lstat(path):
        result = original_lstat(path)
        return ReparseStat(result) if path == payload else result

    monkeypatch.setattr(Path, "lstat", reparse_lstat)

    with pytest.raises(install.LifecycleError) as caught:
        install._validate_module_zip(payload)
    assert caught.value.reason == "unsafe_module_zip_source"


def test_module_zip_extraction_revalidates_published_stage_readback(tmp_path, monkeypatch):
    from dcc_mcp_maya import install

    payload = tmp_path / "module.zip"
    stage = tmp_path / "stage"
    _write_provenanced_module_zip(install, payload)
    real_replace = install._replace_path

    def replace_then_tamper(source, destination):
        real_replace(source, destination)
        if destination == stage:
            (stage / "python" / "dcc_mcp_maya" / "__init__.py").write_bytes(b"TAMPERED_AFTER_PUBLICATION = True\n")

    monkeypatch.setattr(install, "_replace_path", replace_then_tamper)

    with pytest.raises(install.LifecycleError) as caught:
        install._extract_module_zip(payload, stage)
    assert caught.value.reason == "module_zip_publication_mismatch"
    assert not stage.exists()


def test_module_zip_readback_rejects_same_bytes_new_object_race(tmp_path, monkeypatch):
    from dcc_mcp_maya import install

    payload = tmp_path / "module.zip"
    stage = tmp_path / "stage"
    target = stage / "python" / "dcc_mcp_maya" / "__init__.py"
    _write_provenanced_module_zip(install, payload)
    original_open = Path.open
    replaced = False

    def replace_before_read(path, *args, **kwargs):
        nonlocal replaced
        mode = args[0] if args else kwargs.get("mode", "r")
        if path == target and mode == "rb" and not replaced:
            replacement = target.with_name("replacement.py")
            original_open(replacement, "wb").close()
            replacement.replace(target)
            replaced = True
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_before_read)

    with pytest.raises(install.LifecycleError) as caught:
        install._extract_module_zip(payload, stage)
    assert replaced
    assert caught.value.reason == "module_zip_publication_mismatch"
    assert not stage.exists()


@pytest.mark.parametrize(
    "drift",
    ("payload", "digest", "size", "path", "identity", "metadata_digest", "metadata_size", "metadata_path"),
)
def test_module_zip_rejects_core_provenance_drift_before_writes(drift, tmp_path):
    from dcc_mcp_maya import install

    payload = tmp_path / ("core-provenance-%s.zip" % drift)

    def mutate(entries, provenance):
        record = provenance["roots"]["python"]["files"][0]
        if drift == "payload":
            entries[record["path"]] = b'raise RuntimeError("replaced")\n'
        elif drift == "digest":
            record["sha256"] = "0" * 64
        elif drift == "size":
            record["size"] += 1
        elif drift == "path":
            record["path"] = "python/dcc_mcp_core/replaced.py"
        elif drift == "identity":
            provenance["name"] = "dcc_mcp_core"
        elif drift == "metadata_digest":
            provenance["roots"]["python"]["metadata"]["sha256"] = "0" * 64
        elif drift == "metadata_size":
            provenance["roots"]["python"]["metadata"]["size"] += 1
        elif drift == "metadata_path":
            provenance["roots"]["python"]["metadata"]["path"] = "python/vendor/METADATA"

    _write_provenanced_module_zip(install, payload, mutate=mutate)

    with pytest.raises(install.LifecycleError) as caught:
        install._validate_module_zip(payload)
    assert caught.value.reason == "module_zip_core_provenance_mismatch"


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
