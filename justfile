# dcc-mcp-maya development justfile
# Unified dependency and task management

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
set shell := ["bash", "-c"]
set dotenv-load := true

# Default recipe
default:
    @just --list

# ============================================================================
# Dependency Management
# ============================================================================

# Install development dependencies
@install-dev:
    echo "🔧 Installing development dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
    python -m pip install -r requirements-test.txt
    echo "✅ Development dependencies installed"

# Install minimal dependencies (production only)
@install-prod:
    echo "🔧 Installing production dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -e .
    echo "✅ Production dependencies installed"

# Install all dependencies (dev + test + build)
@install-all: install-dev
    echo "✅ All dependencies ready"

# Verify dependency installation
@verify-deps:
    echo "🔍 Verifying dependency installation..."
    python -c "from dcc_mcp_maya import start_server; print('✓ dcc_mcp_maya')"
    python -c "from dcc_mcp_core import create_skill_server; print('✓ dcc_mcp_core')"
    python -c "import pytest; print('✓ pytest')"
    python -c "import requests; print('✓ requests')"
    echo "✅ All core dependencies verified"

# ============================================================================
# Linting & Code Quality
# ============================================================================

# Run ruff check on src/ and tests/
@lint:
    echo "🔍 Running ruff lint check..."
    python -m ruff check src/ tests/
    echo "✅ Lint check passed"

# Auto-fix ruff errors
@lint-fix:
    echo "🔧 Auto-fixing ruff errors..."
    python -m ruff check --fix src/ tests/
    echo "✅ Lint errors fixed"

# Lint SKILL.md files
@lint-skills:
    echo "🔍 Linting SKILL.md files..."
    python tools/lint_skills.py --error-only
    echo "✅ SKILL.md lint passed"

# Build VitePress docs and fail on dead links
@lint-docs:
    echo "🔍 Building docs and checking links..."
    npm --prefix docs run build
    echo "✅ Docs build passed"

# Run all lint checks
lint-all: lint lint-skills lint-docs
    echo "✅ All lint checks passed"

# Pre-commit gate: auto-fix, format, annotate, lint, quick tests.
# Run this before every commit/push to avoid CI failures.
# Usage: vx just prek   or   just prek
@prek:
    echo "🔧 Auto-fixing ruff errors..."
    python -m ruff check --fix src/ tests/
    echo "🎨 Formatting with ruff..."
    python -m ruff format src/ tests/
    echo "🏷️  Running skill affinity annotator (idempotency check)..."
    python tools/annotate_skill_affinity.py --skills-root src/dcc_mcp_maya/skills
    echo "🔍 Running all lint checks..."
    python -m ruff check src/ tests/
    python tools/lint_skills.py --error-only
    npm --prefix docs run build
    echo "🧪 Running quick tests..."
    python -m pytest tests/ -x -q --ignore=tests/test_e2e_maya_standalone.py
    echo "✅ prek passed — safe to commit"

# ============================================================================
# Testing
# ============================================================================

# Run basic import tests
@test-imports:
    echo "🧪 Running import tests..."
    python -m pytest tests/test_basic_imports.py -v
    echo "✅ Import tests passed"

# Run hotreload tests
@test-hotreload:
    echo "🧪 Running hotreload tests..."
    python -m pytest tests/test_hotreload.py -v
    echo "✅ Hotreload tests passed"

# Run gateway integration tests
@test-gateway:
    echo "🧪 Running gateway integration tests..."
    python -m pytest tests/test_gateway_integration.py -v
    echo "✅ Gateway tests passed"

# Run all quick tests (no mayapy required)
@test-quick: test-imports test-hotreload test-gateway
    echo "✅ All quick tests passed"

# Live local smoke test: real MCP HTTP server, lazy-load verification, multi-version gateway
@test-smoke:
    echo "🧪 Running live local smoke test (real MCP HTTP server)..."
    python tools/live_smoke.py
    echo "✅ Live smoke test passed"

# Run tests with coverage
@test-coverage:
    echo "🧪 Running tests with coverage..."
    python -m pytest --cov=dcc_mcp_maya --cov-report=term-missing tests/
    echo "✅ Tests complete with coverage report"

# Run specific test file
@test file="tests/test_basic_imports.py":
    python -m pytest {{file}} -v

# ============================================================================
# Development Workflow
# ============================================================================

# Setup development environment (install + verify)
@setup: install-dev verify-deps
    echo "✅ Development environment ready"

# Check code before commit (lint + quick tests)
@check: lint test-quick
    echo "✅ All checks passed - ready to commit"

# Full CI simulation (lint + tests)
@ci: lint-all test-coverage
    echo "✅ CI simulation complete"

# Local gate: lint + quick tests + live smoke (fast; no mayapy)
@gate: lint-all test-quick test-smoke
    echo "✅ Local gate passed"

# Clean build artifacts
@clean:
    echo "🧹 Cleaning build artifacts..."
    rm -rf build/ dist/ *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    echo "✅ Cleaned"

# Full clean (including test cache)
@clean-all: clean
    echo "🧹 Deep cleaning..."
    rm -rf .pytest_cache .ruff_cache .coverage htmlcov/
    rm -rf tests/.pytest_cache
    echo "✅ Fully cleaned"

# ============================================================================
# Help & Info
# ============================================================================

# Show Python and dependency versions
@versions:
    echo "📦 Environment Information:"
    python --version
    echo ""
    echo "Key Packages:"
    python -m pip show dcc-mcp-core | grep Version
    python -m pip show pytest | grep Version
    python -m pip show ruff | grep Version
    python -m pip show requests | grep Version

# Show dependency tree
@deps-tree:
    echo "📦 Dependency tree (core packages):"
    python -m pip show dcc-mcp-maya -f | grep "Location\|Requires"
    echo ""
    python -m pip show dcc-mcp-core -f | grep "Location\|Requires"

# ============================================================================
# CI/CD Utilities  
# ============================================================================

# Install CI dependencies (for GitHub Actions)
@install-ci: install-dev
    echo "✅ CI dependencies ready"

# Run CI checks locally
@run-ci: clean lint-all test-quick
    echo "✅ Local CI checks passed"

# ============================================================================
# Troubleshooting
# ============================================================================

# Diagnose dependency issues
@diagnose:
    echo "🔍 Diagnosing environment..."
    echo ""
    echo "Python version:"
    python --version
    echo ""
    echo "Pip version:"
    python -m pip --version
    echo ""
    echo "Installed packages (key ones):"
    python -m pip list | grep -E "dcc-mcp|pytest|ruff|requests"
    echo ""
    echo "Trying imports:"
    python -c "from dcc_mcp_maya import start_server; print('✓ dcc_mcp_maya imports OK')" 2>&1 || echo "✗ dcc_mcp_maya import failed"
    python -c "from dcc_mcp_core import create_skill_server; print('✓ dcc_mcp_core imports OK')" 2>&1 || echo "✗ dcc_mcp_core import failed"
    echo ""
    echo "✅ Diagnostic complete"

# Reinstall all dependencies from scratch
@reinstall-all: clean-all
    echo "🔧 Removing pip cache..."
    python -m pip cache purge
    echo "🔧 Reinstalling all dependencies..."
    just install-all
    just verify-deps
    echo "✅ Full reinstall complete"

# Fix common dependency issues
@fix-deps:
    echo "🔧 Attempting to fix dependency issues..."
    echo "  - Upgrading pip..."
    python -m pip install --upgrade pip setuptools wheel
    echo "  - Installing core dependencies..."
    python -m pip install -e .
    echo "  - Installing dev dependencies..."
    python -m pip install -e ".[dev]"
    echo "  - Installing test requirements..."
    python -m pip install -r requirements-test.txt
    echo "✅ Dependency issues fixed"

# ============================================================================
# Maya Local Development
# ============================================================================

# Maya version for local dev (override: just maya-version=2025 maya-link)
maya-version := env("MAYA_VERSION", "2025")

# Detect Maya modules directory (platform-aware)
_maya-modules-dir := if os() == "windows" {
    env("USERPROFILE", "") + "/Documents/maya/modules"
} else if os() == "macos" {
    env("HOME", "") + "/Library/Preferences/Autodesk/maya/modules"
} else {
    env("HOME", "") + "/maya/modules"
}

# Create symlinks from source tree into Maya's module directory for live development.
# After running this, loading Maya will use your local source code directly —
# edits take effect on next Maya restart (or via hot-reload).
@maya-link:
    #!/usr/bin/env bash
    set -euo pipefail
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd || pwd)"
    # On Windows in Git Bash, use the script's real location
    if [ -f "justfile" ]; then PROJECT_ROOT="$(pwd)"; fi

    MOD_DIR="{{ _maya-modules-dir }}"
    TARGET="$MOD_DIR/dcc-mcp-maya"

    echo "🔗 Setting up Maya dev symlinks (Maya {{ maya-version }})..."
    echo "   Project  : $PROJECT_ROOT"
    echo "   Module   : $TARGET"
    echo ""

    # Create modules dir if needed
    mkdir -p "$MOD_DIR"

    # Remove old link/dir if exists
    if [ -L "$TARGET" ]; then
        rm "$TARGET"
        echo "   Removed old symlink"
    elif [ -d "$TARGET" ]; then
        echo "   ⚠️  $TARGET is a real directory (not a symlink)."
        echo "   Remove it manually if you want to use dev symlinks."
        exit 1
    fi

    # Create module directory structure
    mkdir -p "$TARGET/plug-ins"
    mkdir -p "$TARGET/scripts"

    # Symlink python package
    if [ "$(uname -s)" = "MINGW"* ] || [ "$(uname -s)" = "MSYS"* ] || [ -n "${WINDIR:-}" ]; then
        # Windows (Git Bash): use mklink (requires admin or developer mode)
        cmd //c "mklink /D \"$(cygpath -w "$TARGET/python")\" \"$(cygpath -w "$PROJECT_ROOT/src")\"" 2>/dev/null || \
            { echo "   ⚠️  Symlink failed, copying instead..."; cp -r "$PROJECT_ROOT/src" "$TARGET/python"; }
        cmd //c "mklink \"$(cygpath -w "$TARGET/plug-ins/dcc_mcp_maya_plugin.py")\" \"$(cygpath -w "$PROJECT_ROOT/maya/plugin/dcc_mcp_maya_plugin.py")\"" 2>/dev/null || \
            cp "$PROJECT_ROOT/maya/plugin/dcc_mcp_maya_plugin.py" "$TARGET/plug-ins/"
        cmd //c "mklink \"$(cygpath -w "$TARGET/scripts/userSetup.py")\" \"$(cygpath -w "$PROJECT_ROOT/maya/userSetup.py")\"" 2>/dev/null || \
            cp "$PROJECT_ROOT/maya/userSetup.py" "$TARGET/scripts/"
    else
        # Unix: symlinks just work
        ln -sf "$PROJECT_ROOT/src" "$TARGET/python"
        ln -sf "$PROJECT_ROOT/maya/plugin/dcc_mcp_maya_plugin.py" "$TARGET/plug-ins/dcc_mcp_maya_plugin.py"
        ln -sf "$PROJECT_ROOT/maya/userSetup.py" "$TARGET/scripts/userSetup.py"
    fi

    # Generate .mod file
    echo "+ dcc-mcp-maya 0.0.0-dev $TARGET" > "$MOD_DIR/dcc-mcp-maya.mod"
    echo "PYTHONPATH+:=python" >> "$MOD_DIR/dcc-mcp-maya.mod"
    echo "MAYA_PLUG_IN_PATH+:=plug-ins" >> "$MOD_DIR/dcc-mcp-maya.mod"
    echo "MAYA_SCRIPT_PATH+:=scripts" >> "$MOD_DIR/dcc-mcp-maya.mod"

    echo ""
    echo "   ✅ Symlinks created:"
    echo "      python/     → src/ (live source)"
    echo "      plug-ins/   → maya/plugin/"
    echo "      scripts/    → maya/userSetup.py"
    echo "      .mod file   → $MOD_DIR/dcc-mcp-maya.mod"
    echo ""
    echo "   Next: start Maya {{ maya-version }} — the plugin loads automatically."
    echo "   Edit source → restart Maya (or use hot-reload) to see changes."

# Windows version: Create symlinks using PowerShell (for native Windows without Git Bash)
@maya-link-win:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/maya-link-win.ps1 -MayaVersion {{ maya-version }}

# Windows: build dcc-mcp-core with **this Maya's mayapy**, then symlink both
# `dcc_mcp_core` (from core's `python/dcc_mcp_core`) and `dcc_mcp_maya` (from `src/dcc_mcp_maya`)
# into `%USERPROFILE%/Documents/maya/modules/dcc-mcp-maya/python/`. Then start Maya for debugging.
#
# After run, use MCP URL printed below; see `docs/guide/local-mcp-debug.md` for Cursor + debugpy.
# Default core repo: sibling directory `../dcc-mcp-core` or env `DCC_MCP_CORE_REPO`.
# Requires: Git, Rust (cargo), Maya installed under `Program Files/Autodesk/Maya<ver>/`.
#
#   just maya-dev-build-link-core-win
#   just maya-dev-debug-win
#   just maya-version=2024 maya-dev-debug-win
@maya-dev-build-link-core-win:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/maya-dev-build-link-core-win.ps1 -MayaVersion {{ maya-version }}

@maya-dev-debug-win:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/maya-dev-build-link-core-win.ps1 -MayaVersion {{ maya-version }} -LaunchMaya

# Windows: only refresh symlinks (skip maturin develop) after you already built core.
@maya-dev-relink-core-win:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/maya-dev-build-link-core-win.ps1 -MayaVersion {{ maya-version }} -SkipBuild

# Windows: copy a **local** dcc-mcp-core wheel + dcc-mcp-maya sources into
# %USERPROFILE%/Documents/maya (no PyPI). Does not touch git remotes.
#
# 1) Build core wheel (same machine / same Python ABI as your Maya, e.g. cp311 for Maya 2025):
#      cd ../dcc-mcp-core && vx just build
# 2) From this repo:
#      just maya-local-mod-win ABI3_WHEEL=G:/PycharmProjects/github/dcc-mcp-core/dist/dcc_mcp_core-0.15.9-cp311-cp311-win_amd64.whl
# Maya 2022 (cp37): also pass a cp37 wheel:
#      just maya-local-mod-win2022 ABI3_WHEEL=...cp38-abi3...whl CP37_WHEEL=...cp37-cp37m...whl
@maya-local-mod-win ABI3_WHEEL:
    python packaging/assemble_mod_local.py --abi3-wheel "{{ABI3_WHEEL}}"

@maya-local-mod-win2022 ABI3_WHEEL CP37_WHEEL:
    python packaging/assemble_mod_local.py --abi3-wheel "{{ABI3_WHEEL}}" --cp37-wheel "{{CP37_WHEEL}}"

# Remove dev symlinks and .mod file
@maya-unlink:
    #!/usr/bin/env bash
    set -euo pipefail
    MOD_DIR="{{ _maya-modules-dir }}"
    TARGET="$MOD_DIR/dcc-mcp-maya"
    MOD_FILE="$MOD_DIR/dcc-mcp-maya.mod"

    echo "🧹 Removing Maya dev symlinks..."

    if [ -d "$TARGET" ]; then
        rm -rf "$TARGET"
        echo "   Removed $TARGET"
    fi
    if [ -f "$MOD_FILE" ]; then
        rm "$MOD_FILE"
        echo "   Removed $MOD_FILE"
    fi

    echo "   ✅ Dev symlinks cleaned up"

# Windows version: Remove dev symlinks using PowerShell
@maya-unlink-win:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/maya-unlink-win.ps1

# Show current Maya dev link status
@maya-status:
    #!/usr/bin/env bash
    MOD_DIR="{{ _maya-modules-dir }}"
    TARGET="$MOD_DIR/dcc-mcp-maya"
    MOD_FILE="$MOD_DIR/dcc-mcp-maya.mod"

    echo "📋 Maya dev link status:"
    echo "   Modules dir: $MOD_DIR"
    echo ""

    if [ -L "$TARGET/python" ]; then
        REAL=$(readlink "$TARGET/python" 2>/dev/null || echo "?")
        echo "   ✅ python/   → $REAL (symlink)"
    elif [ -d "$TARGET/python" ]; then
        echo "   ⚠️  python/   exists (copied, not linked)"
    else
        echo "   ❌ python/   not found"
    fi

    if [ -L "$TARGET/plug-ins/dcc_mcp_maya_plugin.py" ]; then
        echo "   ✅ plug-ins/ → linked"
    elif [ -f "$TARGET/plug-ins/dcc_mcp_maya_plugin.py" ]; then
        echo "   ⚠️  plug-ins/ exists (copied)"
    else
        echo "   ❌ plug-ins/ not found"
    fi

    if [ -f "$MOD_FILE" ]; then
        echo "   ✅ .mod file  exists"
    else
        echo "   ❌ .mod file  not found"
    fi

# Windows version: Show Maya dev link status using PowerShell
@maya-status-win:
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/maya-status-win.ps1

# Install dcc-mcp-core into Maya's Python (requires mayapy on PATH)
@maya-install-core maya-py="mayapy":
    #!/usr/bin/env bash
    set -euo pipefail
    echo "📦 Installing dcc-mcp-core into Maya Python..."
    {{ maya-py }} -m pip install dcc-mcp-core --upgrade
    echo "✅ dcc-mcp-core installed into Maya Python"

# Windows version: Install dcc-mcp-core into Maya's Python
@maya-install-core-win maya-version="{{ maya-version }}":
    powershell -NoProfile -ExecutionPolicy Bypass -File tools/maya-install-core-win.ps1 -MayaVersion {{ maya-version }}
# Full local dev setup: link + install core into Maya Python
maya-dev: maya-link
    @echo ""
    @echo "📋 Dev environment linked. Now install dcc-mcp-core into Maya:"
    @echo "   Unix/macOS:"
    @echo "     just maya-install-core maya-py=/path/to/mayapy"
    @echo "     or if mayapy is on PATH:"
    @echo "     just maya-install-core"
    @echo ""
    @echo "   Windows (PowerShell):"
    @echo "     just maya-link-win"
    @echo "     just maya-install-core-win maya-version={{ maya-version }}"
    @echo ""
    @echo "   Then verify with:"
    @echo "     just maya-status       # Unix/macOS"
    @echo "     just maya-status-win   # Windows"
