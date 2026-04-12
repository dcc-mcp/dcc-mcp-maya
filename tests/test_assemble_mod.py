"""Tests for packaging/assemble_mod.py — validates the .mod module assembly logic.

These tests verify:
- resolve_core_version: reads minimum version from pyproject.toml and resolves latest from PyPI
- download_core_wheels: finds and downloads correct wheel files via PyPI JSON API
- extract_wheel: correctly extracts wheel contents using zipfile
- generate_mod_file: generates proper .mod content with python37 support
- assemble: end-to-end assembly produces correct directory structure
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
ASSEMBLE_MOD = Path(__file__).parent.parent / "packaging" / "assemble_mod.py"
PROJECT_ROOT = Path(__file__).parent.parent

# We import by executing the script as a module
import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location("assemble_mod", str(ASSEMBLE_MOD))
assemble_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(assemble_mod)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_fake_wheel(dest: Path, name: str, files: dict[str, bytes]) -> Path:
    """Create a minimal wheel zip at *dest/name* containing *files*.

    Automatically adds a .dist-info/METADATA entry so the wheel looks real.
    If *files* already contains dist-info entries they will be preserved.
    """
    wheel_path = dest / name
    with zipfile.ZipFile(str(wheel_path), "w") as zf:
        for fname, content in files.items():
            zf.writestr(fname, content)
        # Add a minimal dist-info if not already present
        dist_info_prefix = f"{name.split('-')[0]}-{name.split('-')[1]}.dist-info/"
        if not any(f.startswith(dist_info_prefix) for f in files):
            zf.writestr(f"{dist_info_prefix}METADATA", "Metadata-Version: 2.1\nName: dcc-mcp-core\n")
    return wheel_path


def _make_fake_pyproject(dest: Path, core_version: str = "0.12.12") -> Path:
    """Create a minimal pyproject.toml at *dest*."""
    toml_path = dest / "pyproject.toml"
    toml_path.write_text(
        f'[project]\ndependencies = [\n    "dcc-mcp-core>={core_version},<1.0.0",\n]\n',
        encoding="utf-8",
    )
    return toml_path


# ── _version_gte ─────────────────────────────────────────────────────────────


class TestVersionGte:
    def test_equal(self):
        assert assemble_mod._version_gte("0.12.12", "0.12.12") is True

    def test_greater(self):
        assert assemble_mod._version_gte("0.12.17", "0.12.12") is True

    def test_lesser(self):
        assert assemble_mod._version_gte("0.12.11", "0.12.12") is False

    def test_major_greater(self):
        assert assemble_mod._version_gte("1.0.0", "0.12.12") is True


# ── resolve_core_version ────────────────────────────────────────────────────


class TestResolveCoreVersion:
    def test_extracts_minimum_version(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.12.15")
        # Patch PyPI query to fail so we get the minimum version
        with patch("urllib.request.urlopen", side_effect=Exception("offline")):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.12.15"

    def test_uses_pypi_latest_when_available(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.12.12")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"info": {"version": "0.12.17"}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            version = assemble_mod.resolve_core_version(tmp_path)
        assert version == "0.12.17"

    def test_falls_back_when_pypi_version_too_old(self, tmp_path):
        _make_fake_pyproject(tmp_path, "0.12.12")
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"info": {"version": "0.12.10"}}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            version = assemble_mod.resolve_core_version(tmp_path)
        # Should fall back to minimum version since 0.12.10 < 0.12.12
        assert version == "0.12.12"

    def test_raises_when_no_version_found(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = []\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="Cannot find dcc-mcp-core version"):
            assemble_mod.resolve_core_version(tmp_path)


# ── download_core_wheels ────────────────────────────────────────────────────


class TestDownloadCoreWheels:
    def _mock_pypi_response(self, version: str = "0.12.17") -> dict:
        """Build a minimal PyPI JSON response for dcc-mcp-core."""
        return {
            "info": {"version": version},
            "urls": [
                {
                    "filename": f"dcc_mcp_core-{version}-cp38-abi3-win_amd64.whl",
                    "url": f"https://example.com/dcc_mcp_core-{version}-cp38-abi3-win_amd64.whl",
                    "packagetype": "bdist_wheel",
                },
                {
                    "filename": f"dcc_mcp_core-{version}-cp37-cp37m-win_amd64.whl",
                    "url": f"https://example.com/dcc_mcp_core-{version}-cp37-cp37m-win_amd64.whl",
                    "packagetype": "bdist_wheel",
                },
                {
                    "filename": f"dcc_mcp_core-{version}-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                    "url": f"https://example.com/dcc_mcp_core-{version}-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                    "packagetype": "bdist_wheel",
                },
                {
                    "filename": f"dcc_mcp_core-{version}-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                    "url": f"https://example.com/dcc_mcp_core-{version}-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                    "packagetype": "bdist_wheel",
                },
                {
                    "filename": f"dcc_mcp_core-{version}-cp38-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl",
                    "url": f"https://example.com/dcc_mcp_core-{version}-cp38-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl",
                    "packagetype": "bdist_wheel",
                },
            ],
            "releases": {
                version: [
                    {
                        "filename": f"dcc_mcp_core-{version}-cp38-abi3-win_amd64.whl",
                        "url": f"https://example.com/dcc_mcp_core-{version}-cp38-abi3-win_amd64.whl",
                        "packagetype": "bdist_wheel",
                    },
                    {
                        "filename": f"dcc_mcp_core-{version}-cp37-cp37m-win_amd64.whl",
                        "url": f"https://example.com/dcc_mcp_core-{version}-cp37-cp37m-win_amd64.whl",
                        "packagetype": "bdist_wheel",
                    },
                    {
                        "filename": f"dcc_mcp_core-{version}-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                        "url": f"https://example.com/dcc_mcp_core-{version}-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                        "packagetype": "bdist_wheel",
                    },
                    {
                        "filename": f"dcc_mcp_core-{version}-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                        "url": f"https://example.com/dcc_mcp_core-{version}-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
                        "packagetype": "bdist_wheel",
                    },
                    {
                        "filename": f"dcc_mcp_core-{version}-cp38-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl",
                        "url": f"https://example.com/dcc_mcp_core-{version}-cp38-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl",
                        "packagetype": "bdist_wheel",
                    },
                ],
            },
        }

    def test_win64_downloads_two_wheels(self, tmp_path):
        pypi_data = self._mock_pypi_response()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(pypi_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(url, dest):
            # Create a minimal wheel file at dest
            fname = Path(dest).name
            if "abi3" in fname:
                files = {"dcc_mcp_core/__init__.py": b"# abi3", "dcc_mcp_core/_core.pyd": b"\x00abi3"}
            else:
                files = {"dcc_mcp_core/__init__.py": b"# cp37", "dcc_mcp_core/_core.pyd": b"\x00cp37"}
            _make_fake_wheel(Path(dest).parent, fname, files)

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheels = assemble_mod.download_core_wheels("0.12.17", "win64", tmp_path)
        assert len(wheels) == 2
        names = [w.name for w in wheels]
        assert any("abi3" in n for n in names)
        assert any("cp37" in n for n in names)

    def test_linux_downloads_two_wheels(self, tmp_path):
        pypi_data = self._mock_pypi_response()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(pypi_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(url, dest):
            fname = Path(dest).name
            files = {"dcc_mcp_core/__init__.py": b"# linux", "dcc_mcp_core/_core.so": b"\x00linux"}
            _make_fake_wheel(Path(dest).parent, fname, files)

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheels = assemble_mod.download_core_wheels("0.12.17", "linux", tmp_path)
        assert len(wheels) == 2

    def test_macos_downloads_one_wheel(self, tmp_path):
        pypi_data = self._mock_pypi_response()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(pypi_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(url, dest):
            fname = Path(dest).name
            files = {"dcc_mcp_core/__init__.py": b"# macos", "dcc_mcp_core/_core.so": b"\x00macos"}
            _make_fake_wheel(Path(dest).parent, fname, files)

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheels = assemble_mod.download_core_wheels("0.12.17", "macos", tmp_path)
        assert len(wheels) == 1
        assert "abi3" in wheels[0].name

    def test_raises_when_no_wheels_found(self, tmp_path):
        pypi_data = {"info": {"version": "0.12.17"}, "urls": [], "releases": {"0.12.17": []}}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(pypi_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="No dcc-mcp-core wheels"):
                assemble_mod.download_core_wheels("0.12.17", "win64", tmp_path)

    def test_warns_on_missing_pattern(self, tmp_path, capsys):
        """If a wheel pattern has no match, a warning is printed but doesn't fail."""
        pypi_data = {
            "info": {"version": "0.12.17"},
            "urls": [
                {
                    "filename": "dcc_mcp_core-0.12.17-cp38-abi3-win_amd64.whl",
                    "url": "https://example.com/x.whl",
                    "packagetype": "bdist_wheel",
                }
            ],
            "releases": {
                "0.12.17": [
                    {
                        "filename": "dcc_mcp_core-0.12.17-cp38-abi3-win_amd64.whl",
                        "url": "https://example.com/x.whl",
                        "packagetype": "bdist_wheel",
                    }
                ]
            },
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(pypi_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlretrieve(url, dest):
            files = {"dcc_mcp_core/__init__.py": b"# test", "dcc_mcp_core/_core.pyd": b"\x00"}
            _make_fake_wheel(Path(dest).parent, Path(dest).name, files)

        with patch("urllib.request.urlopen", return_value=mock_resp), patch(
            "urllib.request.urlretrieve", side_effect=fake_urlretrieve
        ):
            wheels = assemble_mod.download_core_wheels("0.12.17", "win64", tmp_path)
        # Only abi3 wheel was available; cp37 was missing (warned)
        assert len(wheels) == 1
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "cp37" in captured.out


# ── extract_wheel ───────────────────────────────────────────────────────────


class TestExtractWheel:
    def test_extracts_python_files(self, tmp_path):
        files = {
            "dcc_mcp_core/__init__.py": b"print('hello')",
            "dcc_mcp_core/skill.py": b"class Skill: pass",
            "dcc_mcp_core-0.12.17.dist-info/METADATA": b"Metadata-Version: 2.1",
        }
        wheel = _make_fake_wheel(tmp_path, "dcc_mcp_core-0.12.17-cp38-abi3-win_amd64.whl", files)
        dest = tmp_path / "out"
        dest.mkdir()
        assemble_mod.extract_wheel(wheel, dest)
        assert (dest / "dcc_mcp_core" / "__init__.py").read_bytes() == b"print('hello')"
        assert (dest / "dcc_mcp_core" / "skill.py").read_bytes() == b"class Skill: pass"
        # dist-info should NOT be extracted
        assert not (dest / "dcc_mcp_core-0.12.17.dist-info").exists()

    def test_extensions_only_filters_non_extensions(self, tmp_path):
        files = {
            "dcc_mcp_core/__init__.py": b"print('hello')",
            "dcc_mcp_core/_core.pyd": b"\x00binary",
            "dcc_mcp_core/_core.so": b"\x00binary_linux",
        }
        wheel = _make_fake_wheel(tmp_path, "dcc_mcp_core-0.12.17-cp38-abi3-win_amd64.whl", files)
        dest = tmp_path / "out"
        dest.mkdir()
        # Pre-create __init__.py to test that extensions_only skips it
        (dest / "dcc_mcp_core").mkdir()
        (dest / "dcc_mcp_core" / "__init__.py").write_bytes(b"existing")
        assemble_mod.extract_wheel(wheel, dest, extensions_only=True)
        # __init__.py should NOT be overwritten
        assert (dest / "dcc_mcp_core" / "__init__.py").read_bytes() == b"existing"
        # .pyd should be extracted
        assert (dest / "dcc_mcp_core" / "_core.pyd").read_bytes() == b"\x00binary"

    def test_skips_dist_info(self, tmp_path):
        files = {
            "dcc_mcp_core/__init__.py": b"# ok",
            "dcc_mcp_core-0.12.17.dist-info/METADATA": b"Metadata",
            "dcc_mcp_core-0.12.17.dist-info/RECORD": b"record",
        }
        wheel = _make_fake_wheel(tmp_path, "dcc_mcp_core-0.12.17-cp38-abi3-win_amd64.whl", files)
        dest = tmp_path / "out"
        dest.mkdir()
        assemble_mod.extract_wheel(wheel, dest)
        assert (dest / "dcc_mcp_core" / "__init__.py").exists()
        assert not (dest / "dcc_mcp_core-0.12.17.dist-info").exists()


# ── generate_mod_file ───────────────────────────────────────────────────────


class TestGenerateModFile:
    def test_win64_all_maya_versions(self):
        content = assemble_mod.generate_mod_file("0.2.2", "win64", has_cp37=True)
        lines = content.strip().split("\n")
        assert len(lines) == 8  # 4 maya versions * 2 lines each
        assert "MAYAVERSION:2022" in lines[0]
        assert "python37" in lines[1]
        assert "MAYAVERSION:2023" in lines[2]
        assert "PYTHONPATH+:=python" in lines[3]

    def test_win64_no_cp37(self):
        content = assemble_mod.generate_mod_file("0.2.2", "win64", has_cp37=False)
        # All should use python/ (no python37)
        assert "python37" not in content

    def test_macos_skips_2022(self):
        content = assemble_mod.generate_mod_file("0.2.2", "macos", has_cp37=False)
        assert "MAYAVERSION:2022" not in content
        assert "MAYAVERSION:2023" in content

    def test_linux_all_versions(self):
        content = assemble_mod.generate_mod_file("0.2.2", "linux", has_cp37=True)
        assert "MAYAVERSION:2022" in content
        assert "python37" in content


# ── assemble (integration) ──────────────────────────────────────────────────


class TestAssemble:
    def _setup_project(self, tmp_path: Path) -> Path:
        """Create a minimal project structure for testing assemble()."""
        project = tmp_path / "project"
        project.mkdir()

        # pyproject.toml
        _make_fake_pyproject(project, "0.12.12")

        # Maya plugin
        plugin_dir = project / "maya" / "plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "dcc_mcp_maya.py").write_text("# plugin", encoding="utf-8")

        # userSetup.py
        maya_dir = project / "maya"
        (maya_dir / "userSetup.py").write_text("# userSetup", encoding="utf-8")

        # dcc_mcp_maya package
        pkg_src = project / "src" / "dcc_mcp_maya"
        pkg_src.mkdir(parents=True)
        (pkg_src / "__init__.py").write_text("# maya package", encoding="utf-8")

        # Packaging scripts
        pkg_dir = project / "packaging"
        pkg_dir.mkdir()
        (pkg_dir / "install.bat").write_text("@echo install", encoding="utf-8")
        (pkg_dir / "uninstall.bat").write_text("@echo uninstall", encoding="utf-8")
        (pkg_dir / "install.sh").write_text("#!/bin/bash\necho install", encoding="utf-8")
        (pkg_dir / "uninstall.sh").write_text("#!/bin/bash\necho uninstall", encoding="utf-8")
        (pkg_dir / "README.txt").write_text("Readme", encoding="utf-8")

        return project

    def _mock_download_and_resolve(self, project: Path, tmp_path: Path):
        """Return mock patches for resolve_core_version and download_core_wheels."""
        # Create fake wheels
        abi3_files = {
            "dcc_mcp_core/__init__.py": b"# abi3 init",
            "dcc_mcp_core/_core.pyd": b"\x00abi3_core",
            "dcc_mcp_core/skill.py": b"class Skill: pass",
        }
        cp37_files = {
            "dcc_mcp_core/__init__.py": b"# cp37 init",
            "dcc_mcp_core/_core.pyd": b"\x00cp37_core",
        }

        def fake_download(version, platform, dest):
            _make_fake_wheel(dest, f"dcc_mcp_core-{version}-cp38-abi3-win_amd64.whl", abi3_files)
            if platform in ("win64", "linux"):
                _make_fake_wheel(dest, f"dcc_mcp_core-{version}-cp37-cp37m-win_amd64.whl", cp37_files)
            return list(dest.glob("dcc_mcp_core-*.whl"))

        return fake_download

    def test_win64_creates_python_and_python37(self, tmp_path):
        project = self._setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = self._mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.12.17"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        # Check python/ directory
        assert (result / "python" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python" / "dcc_mcp_core" / "_core.pyd").exists()
        assert (result / "python" / "dcc_mcp_maya" / "__init__.py").exists()

        # Check python37/ directory (cp37 overlay)
        assert (result / "python37" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python37" / "dcc_mcp_maya" / "__init__.py").exists()

        # Check .mod file uses python37 for Maya 2022
        mod_content = (result / "dcc_mcp_maya.mod").read_text(encoding="utf-8")
        assert "python37" in mod_content
        lines = mod_content.strip().split("\n")
        assert "PYTHONPATH+:=python37" in lines[1]  # Line after MAYAVERSION:2022

    def test_macos_no_python37(self, tmp_path):
        project = self._setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()

        abi3_files = {
            "dcc_mcp_core/__init__.py": b"# abi3",
            "dcc_mcp_core/_core.so": b"\x00abi3",
        }

        def fake_download(version, platform, dest):
            _make_fake_wheel(dest, f"dcc_mcp_core-{version}-cp38-abi3-macosx.whl", abi3_files)
            return list(dest.glob("dcc_mcp_core-*.whl"))

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.12.17"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "macos", output)

        assert (result / "python" / "dcc_mcp_core").exists()
        assert not (result / "python37").exists()

    def test_mod_file_structure(self, tmp_path):
        project = self._setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = self._mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.12.17"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        # Verify .mod file
        mod = (result / "dcc_mcp_maya.mod").read_text(encoding="utf-8")
        assert "MAYAVERSION:2022" in mod
        assert "MAYAVERSION:2023" in mod
        assert "MAYAVERSION:2024" in mod
        assert "MAYAVERSION:2025" in mod
        assert "PLATFORM:win64" in mod
        assert "dcc_mcp_maya 0.2.2" in mod

    def test_plugin_and_usersetup_copied(self, tmp_path):
        project = self._setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = self._mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.12.17"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (result / "plug-ins" / "dcc_mcp_maya.py").exists()
        assert (result / "scripts" / "userSetup.py").exists()

    def test_install_scripts_win64(self, tmp_path):
        project = self._setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()
        fake_download = self._mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.12.17"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "win64", output)

        assert (result / "install.bat").exists()
        assert (result / "uninstall.bat").exists()
        assert not (result / "install.sh").exists()

    def test_install_scripts_linux(self, tmp_path):
        project = self._setup_project(tmp_path)
        output = tmp_path / "output"
        output.mkdir()

        abi3_files = {"dcc_mcp_core/__init__.py": b"# test", "dcc_mcp_core/_core.so": b"\x00"}
        cp37_files = {"dcc_mcp_core/__init__.py": b"# test", "dcc_mcp_core/_core.so": b"\x00cp37"}

        def fake_download(version, platform, dest):
            _make_fake_wheel(dest, f"dcc_mcp_core-{version}-cp38-abi3-manylinux.whl", abi3_files)
            _make_fake_wheel(dest, f"dcc_mcp_core-{version}-cp37-cp37m-manylinux.whl", cp37_files)
            return list(dest.glob("dcc_mcp_core-*.whl"))

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.12.17"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            result = assemble_mod.assemble(project, "0.2.2", "linux", output)

        assert (result / "install.sh").exists()
        assert (result / "uninstall.sh").exists()
        assert not (result / "install.bat").exists()

    def test_zip_created_by_main(self, tmp_path):
        """Test that main() creates the ZIP archive."""
        project = self._setup_project(tmp_path)
        output = tmp_path / "output"
        fake_download = self._mock_download_and_resolve(project, tmp_path)

        with patch.object(assemble_mod, "resolve_core_version", return_value="0.12.17"), patch.object(
            assemble_mod, "download_core_wheels", side_effect=fake_download
        ):
            # Call main with mocked args
            import sys as real_sys

            old_argv = real_sys.argv
            try:
                real_sys.argv = [
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
                real_sys.argv = old_argv

        # Verify ZIP was created
        zip_files = list(output.glob("*.zip"))
        assert len(zip_files) == 1
        assert "0.2.2-win64" in zip_files[0].name


# ── Live integration test (requires network) ────────────────────────────────


@pytest.mark.packaging
class TestAssembleLive:
    """Live tests that actually contact PyPI.

    Run with: pytest tests/test_assemble_mod.py -m packaging -v

    These are skipped by default because they require network access
    and are slow.
    """

    def test_resolve_core_version_from_real_pypi(self):
        """Verify resolve_core_version can reach real PyPI."""
        version = assemble_mod.resolve_core_version(PROJECT_ROOT)
        # Should return a version >= 0.12.12
        assert assemble_mod._version_gte(version, "0.12.12")

    def test_download_win64_wheels_from_pypi(self, tmp_path):
        """Verify downloading real wheels for win64."""
        version = assemble_mod.resolve_core_version(PROJECT_ROOT)
        wheels = assemble_mod.download_core_wheels(version, "win64", tmp_path)
        assert len(wheels) >= 1  # At least the abi3 wheel
        names = [w.name for w in wheels]
        assert any("abi3" in n for n in names)

    def test_full_win64_assemble_from_pypi(self, tmp_path):
        """End-to-end: assemble a .mod module using real PyPI wheels."""
        output = tmp_path / "output"
        output.mkdir()
        result = assemble_mod.assemble(PROJECT_ROOT, "0.2.2", "win64", output)

        # Verify core structure
        assert (result / "dcc_mcp_maya.mod").exists()
        assert (result / "python" / "dcc_mcp_core" / "__init__.py").exists()
        assert (result / "python" / "dcc_mcp_core" / "_core.pyd").exists()
        assert (result / "python" / "dcc_mcp_maya" / "__init__.py").exists()
        assert (result / "plug-ins" / "dcc_mcp_maya.py").exists()
        assert (result / "scripts" / "userSetup.py").exists()

        # If cp37 wheels were available, python37/ should exist
        if (result / "python37").exists():
            assert (result / "python37" / "dcc_mcp_core" / "__init__.py").exists()
            assert (result / "python37" / "dcc_mcp_maya" / "__init__.py").exists()
