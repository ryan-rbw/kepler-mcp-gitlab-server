#!/bin/bash
# scripts/clean.sh - Clean build artifacts and caches

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

CLEAN_DOCKER=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            CLEAN_DOCKER=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --docker    Also remove Docker images"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Cleaning build artifacts..."

# Remove Python bytecode
echo "  Removing Python bytecode..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Remove build artifacts
echo "  Removing build artifacts..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info
rm -rf src/*.egg-info

# Remove coverage and test artifacts
echo "  Removing test and coverage artifacts..."
rm -rf .coverage
rm -rf htmlcov/
rm -rf .pytest_cache/

# Remove mypy cache
echo "  Removing mypy cache..."
rm -rf .mypy_cache/

# Remove ruff cache
echo "  Removing ruff cache..."
rm -rf .ruff_cache/

# Optionally remove Docker images
if [[ "$CLEAN_DOCKER" == true ]]; then
    echo "  Removing Docker images..."
    docker rmi kepler-mcp-gitlab:lint 2>/dev/null || true
    docker rmi kepler-mcp-gitlab:latest 2>/dev/null || true
fi

echo "Clean complete!"
