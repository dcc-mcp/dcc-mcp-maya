#!/usr/bin/env bash
# Local multi-instance test runner
#
# Usage:
#   ./tests/scripts/run_local_tests.sh [test_module] [pytest_options]
#
# Examples:
#   ./tests/scripts/run_local_tests.sh                      # Run all multi-instance tests
#   ./tests/scripts/run_local_tests.sh test_gateway_failover.py
#   ./tests/scripts/run_local_tests.sh test_gateway_failover.py -v -s

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  DCC-MCP-Maya Multi-Instance Test Suite${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

# Check dependencies
echo -e "\n${YELLOW}Checking dependencies...${NC}"

if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python not found${NC}"
    exit 1
fi

if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}✗ pytest not installed${NC}"
    exit 1
fi

if ! python -c "import requests" 2>/dev/null; then
    echo -e "${RED}✗ requests not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies available${NC}"

# Verify Maya is available
echo -e "\n${YELLOW}Checking Maya availability...${NC}"

# Try to find mayapy for 2025 (most recent)
MAYAPY=""
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    MAYAPY="/Applications/Autodesk/Maya2025/Maya.app/Contents/bin/mayapy"
elif [ "$(uname)" == "Linux" ]; then
    # Linux
    MAYAPY="/usr/autodesk/maya2025/bin/mayapy"
else
    # Windows (Git Bash / MSYS2)
    MAYAPY="C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe"
fi

if [ ! -f "$MAYAPY" ]; then
    echo -e "${YELLOW}⚠ mayapy 2025 not found at $MAYAPY${NC}"
    echo -e "${YELLOW}  Multi-instance tests will be skipped${NC}"
    echo -e "${YELLOW}  (This is OK for CI environments without Maya installed)${NC}"
else
    echo -e "${GREEN}✓ mayapy found: $MAYAPY${NC}"
fi

# Prepare test environment
echo -e "\n${YELLOW}Preparing test environment...${NC}"

export PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT/tests/fixtures:${PYTHONPATH:-}"
export DCC_MCP_MAYA_SKILL_PATHS="$PROJECT_ROOT/skills"

# Default gateway port
GATEWAY_PORT=9765

echo -e "  Gateway port: $GATEWAY_PORT"
echo -e "  Project root: $PROJECT_ROOT"
echo -e "  Python path: $PYTHONPATH"

# Determine which tests to run
TEST_MODULE="${1:-}"
PYTEST_ARGS="${@:2}"

if [ -z "$TEST_MODULE" ]; then
    # Run all multi-instance tests
    TEST_MODULES=(
        "test_gateway_failover.py"
        "test_multi_instance_discovery.py"
        "test_scene_update.py"
    )
else
    TEST_MODULES=("$TEST_MODULE")
fi

echo -e "\n${YELLOW}Running tests:${NC}"
for module in "${TEST_MODULES[@]}"; do
    echo "  - $module"
done

# Run pytest
echo -e "\n${YELLOW}───────────────────────────────────────────────────────────${NC}"
echo -e "${YELLOW}Starting pytest...${NC}"
echo -e "${YELLOW}───────────────────────────────────────────────────────────${NC}\n"

cd "$TESTS_DIR"

# Build pytest command
PYTEST_CMD=(
    "pytest"
    "-v"
    "--tb=short"
    "--timeout=180"
    "-p" "no:cacheprovider"  # Disable pytest cache to avoid issues with temp dirs
)

# Add test modules
for module in "${TEST_MODULES[@]}"; do
    PYTEST_CMD+=("$module")
done

# Add any additional pytest arguments
if [ -n "$PYTEST_ARGS" ]; then
    PYTEST_CMD+=($PYTEST_ARGS)
fi

# Execute tests
if python -m "${PYTEST_CMD[@]}"; then
    echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}\n"
    exit 0
else
    RESULT=$?
    echo -e "\n${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ Tests failed (exit code: $RESULT)${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}\n"
    exit $RESULT
fi
