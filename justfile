# dcc-mcp-maya development justfile
# Unified dependency and task management

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
    python -c "from dcc_mcp_core import create_skill_manager; print('✓ dcc_mcp_core')"
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

# Run all lint checks
lint-all: lint lint-skills
    echo "✅ All lint checks passed"

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
    python -c "from dcc_mcp_core import create_skill_manager; print('✓ dcc_mcp_core imports OK')" 2>&1 || echo "✗ dcc_mcp_core import failed"
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
