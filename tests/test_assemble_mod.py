"""Tests for packaging/assemble_mod.py."""

from __future__ import annotations

import base64
import hashlib
import importlib.util as _ilu
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ASSEMBLE_MOD = Path(__file__).parent.parent / "packaging" / "assemble_mod.py"
PROJECT_ROOT = Path(__file__).parent.parent

_spec = _ilu.spec_from_file_location("assemble_mod", str(ASSEMBLE_MOD))
assemble_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(assemble_mod)


def _make_fake_wheel(dest: Path, name: str, files: dict[str, bytes]) -> Path:
    wheel_path = dest / name
    with zipfile.ZipFile(str(wheel_path), "w") as zf:
        for fname, content in files.items():
            zf.writestr(fname, content)
        dist_info_prefix = f"{name.split('-')[0]}-{name.split('-')[1]}.dist-info/"
        if not any(f.startswith(dist_info_prefix) for f in files):
            zf.writestr(f"{dist_info_prefix}METADATA", "Metadata-Version: 2.1\nName: dcc-mcp-core\n")
    return wheel_path


def _make_recorded_core_wheel(
    dest: Path,
    version: str,
    tag: str,
    files: dict[str, bytes],
    metadata_content: bytes | None = None,
) -> Path:
    """Create a Core wheel whose payload is bound by a real wheel RECORD."""
    dist_info = f"dcc_mcp_core-{version}.dist-info"
    entries = dict(files)
    entries[f"{dist_info}/METADATA"] = metadata_content or (
        f"Metadata-Version: 2.1\nName: dcc-mcp-core\nVersion: {version}\n".encode()
    )
    record_rows = []
    for path, content in sorted(entries.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        record_rows.append(f"{path},sha256={digest},{len(content)}")
    record_rows.append(f"{dist_info}/RECORD,,")
    entries[f"{dist_info}/RECORD"] = ("\n".join(record_rows) + "\n").encode()
    return _make_fake_wheel(dest, f"dcc_mcp_core-{version}-{tag}.whl", entries)


def _make_fake_pyproject(dest: Path, core_version: str = "0.15.7", core_upper: str = "1.0.0") -> Path:
    toml_path = dest / "pyproject.toml"
    toml_path.write_text(
        "[project]\ndependencies = [\n"
        f'    "dcc-mcp-core>={core_version},<{core_upper}",\n'
        f'    "dcc-mcp-server>={core_version},<1.0.0",\n'
        "]\n",
        encoding="utf-8",
    )
    return toml_path


class TestVersionGte:
    def test_equal(self):
        assert assemble_mod._version_gte("0.15.0", "0.15.0") is True

    def test_greater(self):
        assert assemble_mod._version_gte("0.15.1", "0.15.0") is True

    def test_lesser(self):
        assert assemble_mod._version_gte("0.14.99", "0.15.0") is False


class TestResolveCoreVersion:
    def test_extracts_minimum_version(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.15.0")
        with patch("urllib.request.urlopen", side_effect=Exception("offline")):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.15.0"

    def test_uses_pypi_latest_when_available(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.15.0")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"releases": {"0.15.0": [], "0.15.2": []}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.15.2"

    def test_falls_back_when_pypi_version_too_old(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.15.0")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"releases": {"0.14.9": [], "0.14.8": []}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.15.0"

    def test_respects_upper_bound_when_pypi_latest_is_too_new(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.19.4", "0.19.5")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"releases": {"0.19.4": [], "0.19.14": []}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.19.4"

    def test_raises_when_no_version_found(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = []\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="Cannot find dcc-mcp-core version"):
            assemble_mod.resolve_core_version(tmp_path)


class TestResolveServerVersion:
    def test_extracts_minimum_version(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.18.17")
        with patch("urllib.request.urlopen", side_effect=Exception("offline")):
            version = assemble_mod.resolve_server_version(tmp_path)
        assert version == "0.18.17"

    def test_raises_when_no_version_found(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = [\n    "dcc-mcp-core>=0.18.17,<1.0.0",\n]\n',
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError, match="Cannot find dcc-mcp-server version"):
            assemble_mod.resolve_server_version(tmp_path)


class TestDownloadCoreWheels:
    def _mock_pypi_response(self, version: str = "0.15.7") -> dict:
        files = [
            f"dcc_mcp_core-{version}-cp37-cp37m-win_amd64.whl",
            f"dcc_mcp_core-{version}-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
            f"dcc_mcp_core-{version}-cp38-abi3-win_amd64.whl",
            f"dcc_mcp_core-{version}-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
            f"dcc_mcp_core-{version}-cp38-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl",
        ]
        urls = [{"filename": fn, "url": f"https://example.com/{fn}", "packagetype": "bdist_wheel"} for fn in files]
        return {"info": {"version": version}, "urls": urls, "releases": {version: urls}}

    def test_win64_downloads_cp37_and_abi3_wheels(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(self._mock_pypi_response()).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(_url, dest):
            _make_fake_wheel(Path(dest).parent, Path(dest).name, {"dcc_mcp_core/__init__.py": b"# abi3"})

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheels = assemble_mod.download_core_wheels("0.15.7", "win64", tmp_path)
        names = {wheel.name for wheel in wheels}
        assert len(wheels) == 2
        assert any("cp37-cp37m" in name for name in names)
        assert any("abi3" in name for name in names)

    def test_linux_downloads_cp37_and_abi3_wheels(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(self._mock_pypi_response()).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(_url, dest):
            _make_fake_wheel(Path(dest).parent, Path(dest).name, {"dcc_mcp_core/__init__.py": b"# linux"})

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheels = assemble_mod.download_core_wheels("0.15.7", "linux", tmp_path)
        names = {wheel.name for wheel in wheels}
        assert len(wheels) == 2
        assert any("cp37-cp37m" in name for name in names)
        assert any("abi3" in name for name in names)

    def test_macos_downloads_abi3_wheel(self, tmp_path):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(self._mock_pypi_response()).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(_url, dest):
            _make_fake_wheel(Path(dest).parent, Path(dest).name, {"dcc_mcp_core/__init__.py": b"# macos"})

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheels = assemble_mod.download_core_wheels("0.15.7", "macos", tmp_path)
        assert len(wheels) == 1
        assert "abi3" in wheels[0].name

    def test_raises_when_no_wheels_found(self, tmp_path):
        pypi_data = {"info": {"version": "0.15.0"}, "urls": [], "releases": {"0.15.0": []}}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(pypi_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="No dcc-mcp-core wheels"):
                assemble_mod.download_core_wheels("0.15.0", "win64", tmp_path)


class TestDownloadServerWheel:
    def test_win64_downloads_server_wheel(self, tmp_path):
        version = "0.18.17"
        filename = f"dcc_mcp_server-{version}-py3-none-win_amd64.whl"
        pypi_data = {
            "info": {"version": version},
            "urls": [{"filename": filename, "url": f"https://example.com/{filename}", "packagetype": "bdist_wheel"}],
            "releases": {
                version: [
                    {"filename": filename, "url": f"https://example.com/{filename}", "packagetype": "bdist_wheel"}
                ]
            },
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(pypi_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(_url, dest):
            _make_fake_wheel(
                Path(dest).parent,
                Path(dest).name,
                {
                    "dcc_mcp_server/__init__.py": b"# server",
                    f"dcc_mcp_server-{version}.data/scripts/dcc-mcp-server.exe": b"server",
                },
            )

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheel = assemble_mod.download_server_wheel(version, "win64", tmp_path)

        assert wheel.name == filename


class TestExtractWheel:
    def test_extracts_python_files(self, tmp_path):
        files = {
            "dcc_mcp_core/__init__.py": b"print('hello')",
            "dcc_mcp_core/skill.py": b"class Skill: pass",
            "dcc_mcp_core-0.15.0.dist-info/METADATA": b"Metadata-Version: 2.1",
        }
        wheel = _make_fake_wheel(tmp_path, "dcc_mcp_core-0.15.0-cp38-abi3-win_amd64.whl", files)
        dest = tmp_path / "out"
        dest.mkdir()
        assemble_mod.extract_wheel(wheel, dest)
        assert (dest / "dcc_mcp_core" / "__init__.py").read_bytes() == b"print('hello')"
        assert (dest / "dcc_mcp_core" / "skill.py").read_bytes() == b"class Skill: pass"
        assert not (dest / "dcc_mcp_core-0.15.0.dist-info").exists()

    def test_extensions_only_filters_non_extensions(self, tmp_path):
        files = {
            "dcc_mcp_core/__init__.py": b"print('hello')",
            "dcc_mcp_core/_core.pyd": b"\x00binary",
        }
        wheel = _make_fake_wheel(tmp_path, "dcc_mcp_core-0.15.0-cp38-abi3-win_amd64.whl", files)
        dest = tmp_path / "out"
        (dest / "dcc_mcp_core").mkdir(parents=True)
        (dest / "dcc_mcp_core" / "__init__.py").write_bytes(b"existing")
        assemble_mod.extract_wheel(wheel, dest, extensions_only=True)
        assert (dest / "dcc_mcp_core" / "__init__.py").read_bytes() == b"existing"
        assert (dest / "dcc_mcp_core" / "_core.pyd").read_bytes() == b"\x00binary"

    def test_extract_server_wheel_maps_scripts_data_dir(self, tmp_path):
        files = {
            "dcc_mcp_server/__init__.py": b"# server",
            "dcc_mcp_server-0.18.17.data/scripts/dcc-mcp-server.exe": b"server-bin",
            "dcc_mcp_server-0.18.17.dist-info/METADATA": b"Metadata-Version: 2.1",
        }
        wheel = _make_fake_wheel(tmp_path, "dcc_mcp_server-0.18.17-py3-none-win_amd64.whl", files)
        dest = tmp_path / "out"
        assemble_mod.extract_server_wheel(wheel, dest)

        assert (dest / "dcc_mcp_server" / "__init__.py").read_bytes() == b"# server"
        assert (dest / "scripts" / "dcc-mcp-server.exe").read_bytes() == b"server-bin"


@pytest.mark.parametrize(
    "metadata_content",
    (
        b"Metadata-Version: 2.1\nName: dcc-mcp-core\nName: attacker-core\nVersion: 0.19.45\n",
        b"Metadata-Version: 2.1\nName: dcc-mcp-core\nVersion: 0.19.45\nVersion: 9.9.9\n",
        b"Metadata-Version: 2.1\nName: dcc-mcp-core\nVersion: not-a-version\n",
        b"Metadata-Version: 2.1\nName: dcc-mcp-core\nVersion: 0.19.45\n 9.9.9\n",
    ),
)
def test_verify_core_wheel_rejects_ambiguous_or_invalid_identity_headers(tmp_path, metadata_content):
    wheel = _make_recorded_core_wheel(
        tmp_path,
        "0.19.45",
        "cp38-abi3-win_amd64",
        {"dcc_mcp_core/__init__.py": b"# core\n"},
        metadata_content=metadata_content,
    )

    with pytest.raises(RuntimeError, match="METADATA|identity"):
        assemble_mod.verify_core_wheel(wheel, "0.19.45")


class TestGenerateModFile:
    def test_win64_relative_path(self):
        content = assemble_mod.generate_mod_file("0.2.2", "win64", path=".")
        lines = content.strip().split("\n")
        assert len(lines) == 15
        assert "MAYAVERSION:2022" in lines[0]
        assert "PYTHONPATH+:=python37" in lines[1]
        assert "MAYAVERSION:2023" in lines[3]
        assert "PYTHONPATH+:=python" in lines[4]
        assert "PLUG_IN_PATH+:=plug-ins" in lines[2]

    def test_absolute_path(self):
        content = assemble_mod.generate_mod_file("0.2.2", "win64", path="C:\\tools\\dcc-mcp-maya")
        assert "C:\\tools\\dcc-mcp-maya" in content

    def test_macos_versions(self):
        content = assemble_mod.generate_mod_file("0.2.2", "macos")
        assert "MAYAVERSION:2022" not in content
        assert "MAYAVERSION:2023" in content
        assert "MAYAVERSION:2026" in content


class TestGenerateModuleInfo:
    def test_module_info(self):
        content = assemble_mod.generate_module_info(
            "0.2.2",
            project_root=PROJECT_ROOT,
            embedded_core_version="0.19.4",
            bundled_server_version="0.18.21",
        )
        info = json.loads(content)
        assert info["name"] == "dcc_mcp_maya"
        assert info["version"] == "0.2.2"
        assert info["adapter_version"] == "0.2.2"
        assert info["embedded_core_version"] == "0.19.4"
        assert info["bundled_server_version"] == "0.18.21"
        assert info["min_core_version"] == "0.19.45"
        assert info["max_core_version_exclusive"] == "1.0.0"
        assert info["has_python37"] is True
        assert info["supported_maya_versions"] == ["2022", "2023", "2024", "2025", "2026"]

    def test_module_info_derives_exact_core_bounds_from_pyproject(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.19.45", "1.0.0")

        info = json.loads(assemble_mod.generate_module_info("0.2.2", project_root=tmp_path))

        assert info["min_core_version"] == "0.19.45"
        assert info["max_core_version_exclusive"] == "1.0.0"


class TestPackagingReadmes:
    def test_module_readmes_document_bundled_sidecar_runtime(self):
        for name in ("README.txt", "README-pipeline.txt"):
            text = (PROJECT_ROOT / "packaging" / name).read_text(encoding="utf-8")
            assert "dcc-mcp-server sidecar binary" in text
            assert "bundled" in text.lower()
            assert "DCC_MCP_SERVER_BIN" in text
            assert "DCC_MCP_MAYA_SIDECAR=0" in text
            assert "resolve_sidecar_binary" in text


class TestPackagingInstallers:
    def test_windows_installer_reads_version_from_generated_mod_contract(self):
        installer = (PROJECT_ROOT / "packaging" / "install.bat").read_text(encoding="utf-8")
        token_match = re.search(r'for /f "tokens=(\d+)" %%v', installer)

        assert token_match is not None
        generated_mod_line = "+ MAYAVERSION:2024 PLATFORM:win64 dcc_mcp_maya 0.9.9 ."
        token_index = int(token_match.group(1)) - 1
        assert generated_mod_line.split()[token_index] == "0.9.9"

    def test_windows_installer_removes_legacy_module_descriptor(self):
        installer = (PROJECT_ROOT / "packaging" / "install.bat").read_text(encoding="utf-8")

        assert 'set "LEGACY_MOD_FILE=%MOD_DEST%\\dcc-mcp-maya.mod"' in installer
        assert 'del /q "%LEGACY_MOD_FILE%"' in installer


def _setup_project(tmp_path: Path, core_version: str = "0.15.0") -> Path:
    project = tmp_path / "project"
    project.mkdir()
    _make_fake_pyproject(project, core_version)

    plugin_dir = project / "maya" / "plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "dcc_mcp_maya_plugin.py").write_text("# plugin", encoding="utf-8")

    maya_dir = project / "maya"
    (maya_dir / "userSetup.py").write_text("# userSetup", encoding="utf-8")

    pkg_src = project / "src" / "dcc_mcp_maya"
    pkg_src.mkdir(parents=True)
    (pkg_src / "__init__.py").write_text("# maya package", encoding="utf-8")

    pkg_dir = project / "packaging"
    pkg_dir.mkdir()
    (pkg_dir / "install.bat").write_text("@echo install", encoding="utf-8")
    (pkg_dir / "uninstall.bat").write_text("@echo uninstall", encoding="utf-8")
    (pkg_dir / "install.sh").write_text("#!/bin/bash\necho install", encoding="utf-8")
    (pkg_dir / "uninstall.sh").write_text("#!/bin/bash\necho uninstall", encoding="utf-8")
    (pkg_dir / "README.txt").write_text("Readme", encoding="utf-8")
    (pkg_dir / "README-pipeline.txt").write_text("Pipeline Readme", encoding="utf-8")

    return project


def _mock_download_and_resolve(_project: Path, _tmp_path: Path):
    abi3_files = {
        "dcc_mcp_core/__init__.py": b"# abi3 init",
        "dcc_mcp_core/_core.pyd": b"\x00abi3_core",
        "dcc_mcp_core/nested/payload.py": b"NESTED_VERIFIED_CORE = True\n",
        "dcc_mcp_core/skill.py": b"class Skill: pass",
    }

    def fake_download(version, _platform, dest):
        cp37_files = dict(abi3_files)
        cp37_files["dcc_mcp_core/_core.pyd"] = b"\x00cp37_core"
        _make_recorded_core_wheel(dest, version, "cp37-cp37m-win_amd64", cp37_files)
        _make_recorded_core_wheel(dest, version, "cp38-abi3-win_amd64", abi3_files)
        return list(dest.glob("dcc_mcp_core-*.whl"))

    return fake_download


def _mock_server_download(version, _platform, dest):
    return _make_fake_wheel(
        dest,
        f"dcc_mcp_server-{version}-py3-none-win_amd64.whl",
        {
            "dcc_mcp_server/__init__.py": b"def binary_path(): pass\n",
            f"dcc_mcp_server-{version}.data/scripts/dcc-mcp-server.exe": b"server-bin",
        },
    )


def _replace_with_directory_link(source: Path, preserved: Path) -> None:
    source.replace(preserved)
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(source), str(preserved)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout
    else:
        source.symlink_to(preserved, target_is_directory=True)


class TestAssemble:
    def test_capture_rejects_file_symlink_without_mutating_target(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_bytes(b"TRUSTED_TARGET = True\n")
        link = tmp_path / "linked.py"
        link.symlink_to(target)

        with pytest.raises(RuntimeError, match="non-reparse single-link regular file"):
            assemble_mod._capture_assembled_file(link)

        assert target.read_bytes() == b"TRUSTED_TARGET = True\n"

    @pytest.mark.parametrize("replace_after_verify", [False, True], ids=["positive-control", "path-swap"])
    def test_assemble_packages_exact_verified_core_bytes(self, tmp_path, replace_after_verify):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        foreign_dir = tmp_path / "foreign"
        foreign_dir.mkdir()
        version = "0.15.0"
        original_source = b"ORIGINAL_VERIFIED_CORE = True\n"
        foreign_source = b"FOREIGN_REPLACEMENT_CORE = True\n"
        foreign_wheel = _make_recorded_core_wheel(
            foreign_dir,
            version,
            "cp38-abi3-win_amd64",
            {
                "dcc_mcp_core/__init__.py": foreign_source,
                "dcc_mcp_core/_core.pyd": b"\x00foreign_core",
            },
        )
        original_wheel_bytes = {}

        def fake_download(core_version, _platform, dest):
            cp37 = _make_recorded_core_wheel(
                dest,
                core_version,
                "cp37-cp37m-win_amd64",
                {
                    "dcc_mcp_core/__init__.py": original_source,
                    "dcc_mcp_core/_core.pyd": b"\x00cp37_core",
                },
            )
            abi3 = _make_recorded_core_wheel(
                dest,
                core_version,
                "cp38-abi3-win_amd64",
                {
                    "dcc_mcp_core/__init__.py": original_source,
                    "dcc_mcp_core/_core.pyd": b"\x00abi3_core",
                },
            )
            original_wheel_bytes[abi3.name] = abi3.read_bytes()
            return [cp37, abi3]

        real_verify = assemble_mod.verify_core_wheel

        def verify_then_replace(wheel, expected_version):
            verified = real_verify(wheel, expected_version)
            if replace_after_verify and "abi3" in wheel.name:
                wheel.write_bytes(foreign_wheel.read_bytes())
            return verified

        with patch.object(assemble_mod, "resolve_core_version", return_value=version), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "verify_core_wheel", side_effect=verify_then_replace), patch.object(
            assemble_mod, "resolve_server_version", return_value=version
        ), patch.object(assemble_mod, "download_server_wheel", side_effect=_mock_server_download):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (result / "python" / "dcc_mcp_core" / "__init__.py").read_bytes() == original_source
        provenance = json.loads((result / assemble_mod.CORE_PROVENANCE_PATH).read_text(encoding="utf-8"))
        abi3_record = next(item for item in provenance["source_wheels"] if "abi3" in item["filename"])
        assert abi3_record["sha256"] == hashlib.sha256(original_wheel_bytes[abi3_record["filename"]]).hexdigest()

    def test_assemble_rejects_core_payload_drift_after_extraction(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)
        real_write_provenance = assemble_mod._write_core_provenance

        def drift_before_provenance(module_dir, *args, **kwargs):
            for root_name in ("python", "python37"):
                target = module_dir / root_name / "dcc_mcp_core" / "__init__.py"
                if target.is_file():
                    target.write_bytes(b"FOREIGN_POST_EXTRACTION_CORE = True\n")
            return real_write_provenance(module_dir, *args, **kwargs)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ), patch.object(assemble_mod, "_write_core_provenance", side_effect=drift_before_provenance):
            with pytest.raises(RuntimeError, match="Core payload changed after verified wheel extraction"):
                assemble_mod.assemble(project, "0.2.2", "win64", output)

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    def test_assemble_rejects_same_bytes_new_core_object_after_extraction(self, tmp_path, root_name):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)
        real_write_provenance = assemble_mod._write_core_provenance

        def replace_before_provenance(module_dir, *args, **kwargs):
            target = module_dir / root_name / "dcc_mcp_core" / "__init__.py"
            replacement = target.with_name("replacement.py")
            replacement.write_bytes(target.read_bytes())
            replacement.replace(target)
            return real_write_provenance(module_dir, *args, **kwargs)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ), patch.object(assemble_mod, "_write_core_provenance", side_effect=replace_before_provenance):
            with pytest.raises(RuntimeError, match="Core payload object changed after verified wheel extraction"):
                assemble_mod.assemble(project, "0.2.2", "win64", output)

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    def test_assemble_rejects_hardlink_before_first_core_identity_binding(self, tmp_path, root_name):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)
        real_bind = assemble_mod._bind_extracted_core_objects
        alias = tmp_path / f"{root_name}-external-alias.py"

        def hardlink_before_bind(module_dir, expected_roots):
            target = module_dir / root_name / "dcc_mcp_core" / "__init__.py"
            os.link(target, alias)
            return real_bind(module_dir, expected_roots)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ), patch.object(assemble_mod, "_bind_extracted_core_objects", side_effect=hardlink_before_bind):
            with pytest.raises(RuntimeError, match="single-link regular file"):
                assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert alias.is_file()

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    def test_assemble_rejects_reparse_core_directory_before_identity_binding(self, tmp_path, root_name):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)
        real_bind = assemble_mod._bind_extracted_core_objects
        preserved = tmp_path / f"{root_name}-preserved-core"

        def replace_root_with_directory_link(module_dir, expected_roots):
            core_root = module_dir / root_name / "dcc_mcp_core"
            core_root.replace(preserved)
            if os.name == "nt":
                result = subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(core_root), str(preserved)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0, result.stderr or result.stdout
            else:
                core_root.symlink_to(preserved, target_is_directory=True)
            return real_bind(module_dir, expected_roots)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ), patch.object(assemble_mod, "_bind_extracted_core_objects", side_effect=replace_root_with_directory_link):
            with pytest.raises(RuntimeError, match="directory must not be a link or reparse point"):
                assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (preserved / "__init__.py").is_file()

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    def test_assemble_rejects_nested_directory_link_before_first_identity_binding(self, tmp_path, root_name):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)
        real_bind = assemble_mod._bind_extracted_core_objects
        preserved = tmp_path / f"{root_name}-preserved-nested-before-bind"

        def replace_nested_before_bind(module_dir, expected_roots):
            nested = module_dir / root_name / "dcc_mcp_core" / "nested"
            _replace_with_directory_link(nested, preserved)
            return real_bind(module_dir, expected_roots)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ), patch.object(assemble_mod, "_bind_extracted_core_objects", side_effect=replace_nested_before_bind):
            with pytest.raises(RuntimeError, match="directory must not be a link or reparse point"):
                assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (preserved / "payload.py").read_bytes() == b"NESTED_VERIFIED_CORE = True\n"

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    def test_bound_core_objects_rejects_nested_directory_link_on_recapture(self, tmp_path, root_name):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            module_dir, expected_roots = assemble_mod.assemble(
                project, "0.2.2", "win64", output, _with_core_contract=True
            )

        nested = module_dir / root_name / "dcc_mcp_core" / "nested"
        preserved = tmp_path / f"{root_name}-preserved-nested-recapture"
        _replace_with_directory_link(nested, preserved)

        with pytest.raises(RuntimeError, match="directory must not be a link or reparse point"):
            assemble_mod._assert_bound_core_objects(module_dir, expected_roots)

        assert (preserved / "payload.py").read_bytes() == b"NESTED_VERIFIED_CORE = True\n"

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    def test_archive_rejects_nested_directory_link_before_consumption(self, tmp_path, root_name):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            module_dir, expected_roots = assemble_mod.assemble(
                project, "0.2.2", "win64", output, _with_core_contract=True
            )

        nested = module_dir / root_name / "dcc_mcp_core" / "nested"
        preserved = tmp_path / f"{root_name}-preserved-nested-before-archive"
        _replace_with_directory_link(nested, preserved)

        with pytest.raises(RuntimeError, match="Core payload changed during archive consumption"):
            assemble_mod._make_bound_archive(output / "nested-before", output, module_dir.name, expected_roots)

        assert (preserved / "payload.py").read_bytes() == b"NESTED_VERIFIED_CORE = True\n"

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    @pytest.mark.parametrize("mutation_timing", ["before", "after"])
    def test_archive_rejects_nested_directory_link_during_consumption(self, tmp_path, root_name, mutation_timing):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            module_dir, expected_roots = assemble_mod.assemble(
                project, "0.2.2", "win64", output, _with_core_contract=True
            )

        real_make_archive = assemble_mod.shutil.make_archive
        preserved = tmp_path / f"{root_name}-preserved-nested-archive-{mutation_timing}"
        mutated = False

        def mutate_around_archive(*args, **kwargs):
            nonlocal mutated
            nested = module_dir / root_name / "dcc_mcp_core" / "nested"
            if mutation_timing == "before":
                _replace_with_directory_link(nested, preserved)
            archive_path = real_make_archive(*args, **kwargs)
            if mutation_timing == "after":
                _replace_with_directory_link(nested, preserved)
            mutated = True
            return archive_path

        with patch.object(assemble_mod.shutil, "make_archive", side_effect=mutate_around_archive):
            with pytest.raises(RuntimeError, match="Core payload changed during archive consumption"):
                assemble_mod._make_bound_archive(output / "nested-window", output, module_dir.name, expected_roots)

        assert mutated
        assert (preserved / "payload.py").read_bytes() == b"NESTED_VERIFIED_CORE = True\n"

    def test_win64_creates_python_and_python37(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (result / "python" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python" / "dcc_mcp_core" / "_core.pyd").exists()
        assert (result / "python" / "dcc_mcp_server" / "__init__.py").exists()
        assert (result / "python" / "scripts" / "dcc-mcp-server.exe").exists()
        assert (result / "python" / "dcc_mcp_maya" / "__init__.py").exists()
        assert (result / "python37" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python37" / "dcc_mcp_core" / "_core.pyd").read_bytes() == b"\x00cp37_core"
        assert (result / "python37" / "dcc_mcp_server" / "__init__.py").exists()
        assert (result / "python37" / "scripts" / "dcc-mcp-server.exe").exists()
        assert (result / "python37" / "dcc_mcp_maya" / "__init__.py").exists()
        info = json.loads((result / "module-info.json").read_text(encoding="utf-8"))
        assert info["adapter_version"] == "0.2.2"
        assert info["embedded_core_version"] == "0.15.0"
        assert info["bundled_server_version"] == "0.15.0"
        assert info["min_core_version"] == "0.15.0"
        assert info["max_core_version_exclusive"] == "1.0.0"

        mod_content = (result / "dcc_mcp_maya.mod").read_text(encoding="utf-8")
        assert "MAYAVERSION:2022" in mod_content
        assert "PYTHONPATH+:=python37" in mod_content
        assert "PYTHONPATH+:=python" in mod_content
        assert " ." in mod_content

    def test_plugin_and_usersetup_copied(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (result / "plug-ins" / "dcc_mcp_maya_plugin.py").exists()
        assert (result / "scripts" / "userSetup.py").exists()


class TestAssemblePortable:
    def test_win64_has_install_scripts(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            result = assemble_mod.assemble_portable(project, "0.2.2", "win64", output)

        assert (result / "install.bat").exists()
        assert (result / "uninstall.bat").exists()
        assert not (result / "install.sh").exists()
        assert (result / "README.txt").exists()
        assert (result / "module-info.json").exists()

    def test_linux_has_install_sh(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            result = assemble_mod.assemble_portable(project, "0.2.2", "linux", output)

        assert (result / "install.sh").exists()
        assert (result / "uninstall.sh").exists()
        assert not (result / "install.bat").exists()


class TestAssemblePipeline:
    def test_has_module_info_and_no_install_scripts(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            result = assemble_mod.assemble_pipeline(project, "0.2.2", "win64", output)

        info = json.loads((result / "module-info.json").read_text(encoding="utf-8"))
        assert info["version"] == "0.2.2"
        assert info["adapter_version"] == "0.2.2"
        assert info["embedded_core_version"] == "0.15.0"
        assert info["bundled_server_version"] == "0.15.0"
        assert info["supported_maya_versions"] == ["2022", "2023", "2024", "2025", "2026"]
        assert info["has_python37"] is True
        assert info["min_core_version"] == "0.15.0"
        assert info["max_core_version_exclusive"] == "1.0.0"
        assert (result / "README-pipeline.txt").exists()
        assert not (result / "install.bat").exists()
        assert not (result / "install.sh").exists()


class TestMain:
    def test_creates_two_zips(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            old_argv = sys.argv
            try:
                sys.argv = [
                    "assemble_mod.py",
                    "--version",
                    "0.2.2",
                    "--platform",
                    "win64",
                    "--output",
                    str(output),
                    "--project-root",
                    str(project),
                ]
                assemble_mod.main()
            finally:
                sys.argv = old_argv

        zip_files = list(output.rglob("*.zip"))
        names = [z.name for z in zip_files]
        assert any("0.2.2-win64.zip" in n for n in names), f"Portable ZIP not found in {names}"
        assert any("0.2.2-win64-pipeline.zip" in n for n in names), f"Pipeline ZIP not found in {names}"
        for zip_file in zip_files:
            with zipfile.ZipFile(zip_file) as zf:
                info = json.loads(zf.read("dcc-mcp-maya/module-info.json").decode())
            assert info["adapter_version"] == "0.2.2"
            assert info["embedded_core_version"] == "0.15.0"
            assert info["bundled_server_version"] == "0.15.0"
            assert info["min_core_version"] == "0.15.0"
            assert info["max_core_version_exclusive"] == "1.0.0"

    @pytest.mark.parametrize("root_name", ["python", "python37"])
    def test_archive_rejects_external_hardlink_mutation_window(self, tmp_path, root_name):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        fake_download = _mock_download_and_resolve(project, tmp_path)
        real_make_archive = assemble_mod.shutil.make_archive
        alias = tmp_path / f"{root_name}-archive-window-alias.py"
        foreign = b"FOREIGN_ARCHIVE_WINDOW_PAYLOAD = True\n"
        mutated = False

        def mutate_inside_archive(*args, **kwargs):
            nonlocal mutated
            if not mutated:
                module_dir = Path(kwargs["root_dir"]) / kwargs["base_dir"]
                target = module_dir / root_name / "dcc_mcp_core" / "__init__.py"
                os.link(target, alias)
                alias.write_bytes(foreign)
                mutated = True
            return real_make_archive(*args, **kwargs)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ), patch.object(assemble_mod.shutil, "make_archive", side_effect=mutate_inside_archive):
            old_argv = sys.argv
            try:
                sys.argv = [
                    "assemble_mod.py",
                    "--version",
                    "0.2.2",
                    "--platform",
                    "win64",
                    "--output",
                    str(output),
                    "--project-root",
                    str(project),
                ]
                with pytest.raises(RuntimeError, match="Core payload changed during archive consumption"):
                    assemble_mod.main()
            finally:
                sys.argv = old_argv

        assert mutated
        assert alias.read_bytes() == foreign

    def test_both_release_zips_preserve_core_provenance_and_validate(self, tmp_path):
        from dcc_mcp_maya import install

        project = _setup_project(tmp_path, install.MIN_CORE_VERSION)
        output = tmp_path / "output"

        def recorded_download(version, _platform, dest):
            common = {
                "dcc_mcp_core/__init__.py": b"# recorded core\n",
                "dcc_mcp_core/skill.py": b"class Skill: pass\n",
            }
            cp37 = dict(common)
            cp37["dcc_mcp_core/_core.pyd"] = b"cp37-core"
            abi3 = dict(common)
            abi3["dcc_mcp_core/_core.pyd"] = b"abi3-core"
            return [
                _make_recorded_core_wheel(dest, version, "cp37-cp37m-win_amd64", cp37),
                _make_recorded_core_wheel(dest, version, "cp38-abi3-win_amd64", abi3),
            ]

        with patch.object(assemble_mod, "resolve_core_version", return_value=install.MIN_CORE_VERSION), patch.object(
            assemble_mod, "download_core_wheels", side_effect=recorded_download
        ), patch.object(assemble_mod, "resolve_server_version", return_value=install.MIN_CORE_VERSION), patch.object(
            assemble_mod, "download_server_wheel", side_effect=_mock_server_download
        ):
            old_argv = sys.argv
            try:
                sys.argv = [
                    "assemble_mod.py",
                    "--version",
                    install.__version__,
                    "--platform",
                    "win64",
                    "--output",
                    str(output),
                    "--project-root",
                    str(project),
                ]
                assemble_mod.main()
            finally:
                sys.argv = old_argv

        zip_files = sorted(output.rglob("*.zip"))
        assert len(zip_files) == 2
        for zip_file in zip_files:
            normalized = install._validate_module_zip(zip_file)
            assert "core-provenance.json" in normalized
            with zipfile.ZipFile(zip_file) as archive:
                provenance = json.loads(archive.read("dcc-mcp-maya/core-provenance.json"))
            assert provenance["name"] == "dcc-mcp-core"
            assert provenance["version"] == install.MIN_CORE_VERSION
            assert set(provenance["roots"]) == {"python", "python37"}
            assert all(root["files"] for root in provenance["roots"].values())


@pytest.mark.packaging
class TestAssembleLive:
    def test_resolve_core_version_from_real_pypi(self):
        version = assemble_mod.resolve_core_version(PROJECT_ROOT)
        assert assemble_mod._version_gte(version, "0.17.19")

    def test_download_win64_wheels_from_pypi(self, tmp_path):
        version = assemble_mod.resolve_core_version(PROJECT_ROOT)
        wheels = assemble_mod.download_core_wheels(version, "win64", tmp_path)
        assert len(wheels) == 2
        assert any("cp37-cp37m" in wheel.name for wheel in wheels)
        assert any("abi3" in wheel.name for wheel in wheels)

    def test_full_win64_assemble_from_pypi(self, tmp_path):
        output = tmp_path / "output"
        output.mkdir()
        result = assemble_mod.assemble(PROJECT_ROOT, "0.2.2", "win64", output)

        assert (result / "dcc_mcp_maya.mod").exists()
        assert (result / "python" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python" / "dcc_mcp_core" / "_core.pyd").exists()
        assert (result / "python" / "dcc_mcp_maya" / "__init__.py").exists()
        assert (result / "plug-ins" / "dcc_mcp_maya_plugin.py").exists()
        assert (result / "scripts" / "userSetup.py").exists()
        assert (result / "python37" / "dcc_mcp_core" / "_core.pyd").exists()
