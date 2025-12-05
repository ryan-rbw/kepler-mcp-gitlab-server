#!/bin/bash
# scripts/lint.sh - Run linting checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

FIX_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fix       Auto-fix linting issues where possible"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Running Ruff linting..."
echo ""

if [[ "$FIX_MODE" == true ]]; then
    echo "Mode: Auto-fix enabled"
    echo ""
    ruff check --fix src/ tests/
else
    echo "Mode: Check only (use --fix to auto-fix)"
    echo ""
    ruff check src/ tests/
fi

echo ""
echo "Linting complete!"
