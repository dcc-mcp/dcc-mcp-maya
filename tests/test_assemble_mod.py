"""Tests for packaging/assemble_mod.py."""

from __future__ import annotations

import importlib.util as _ilu
import json
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


def _make_fake_pyproject(dest: Path, core_version: str = "0.15.7") -> Path:
    toml_path = dest / "pyproject.toml"
    toml_path.write_text(
        f'[project]\ndependencies = [\n    "dcc-mcp-core>={core_version},<1.0.0",\n]\n',
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
        mock_resp.read.return_value = json.dumps({"info": {"version": "0.15.2"}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.15.2"

    def test_falls_back_when_pypi_version_too_old(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.15.0")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"info": {"version": "0.14.9"}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.15.0"

    def test_raises_when_no_version_found(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = []\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="Cannot find dcc-mcp-core version"):
            assemble_mod.resolve_core_version(tmp_path)


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
        content = assemble_mod.generate_module_info("0.2.2")
        info = json.loads(content)
        assert info["name"] == "dcc_mcp_maya"
        assert info["version"] == "0.2.2"
        assert info["has_python37"] is True
        assert info["supported_maya_versions"] == ["2022", "2023", "2024", "2025", "2026"]


def _setup_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    _make_fake_pyproject(project, "0.15.0")

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
        "dcc_mcp_core/skill.py": b"class Skill: pass",
    }

    def fake_download(version, _platform, dest):
        cp37_files = dict(abi3_files)
        cp37_files["dcc_mcp_core/_core.pyd"] = b"\x00cp37_core"
        _make_fake_wheel(dest, f"dcc_mcp_core-{version}-cp37-cp37m-win_amd64.whl", cp37_files)
        _make_fake_wheel(dest, f"dcc_mcp_core-{version}-cp38-abi3-win_amd64.whl", abi3_files)
        return list(dest.glob("dcc_mcp_core-*.whl"))

    return fake_download


class TestAssemble:
    def test_win64_creates_python_and_python37(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (result / "python" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python" / "dcc_mcp_core" / "_core.pyd").exists()
        assert (result / "python" / "dcc_mcp_maya" / "__init__.py").exists()
        assert (result / "python37" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python37" / "dcc_mcp_core" / "_core.pyd").read_bytes() == b"\x00cp37_core"
        assert (result / "python37" / "dcc_mcp_maya" / "__init__.py").exists()

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
        ):
            result = assemble_mod.assemble_portable(project, "0.2.2", "win64", output)

        assert (result / "install.bat").exists()
        assert (result / "uninstall.bat").exists()
        assert not (result / "install.sh").exists()
        assert (result / "README.txt").exists()
        assert not (result / "module-info.json").exists()

    def test_linux_has_install_sh(self, tmp_path):
        project = _setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = _mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.15.0"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
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
        ):
            result = assemble_mod.assemble_pipeline(project, "0.2.2", "win64", output)

        info = json.loads((result / "module-info.json").read_text(encoding="utf-8"))
        assert info["version"] == "0.2.2"
        assert info["supported_maya_versions"] == ["2022", "2023", "2024", "2025", "2026"]
        assert info["has_python37"] is True
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


@pytest.mark.packaging
class TestAssembleLive:
    def test_resolve_core_version_from_real_pypi(self):
        version = assemble_mod.resolve_core_version(PROJECT_ROOT)
        assert assemble_mod._version_gte(version, "0.15.7")

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
