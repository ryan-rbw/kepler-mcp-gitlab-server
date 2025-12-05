#!/bin/bash
# scripts/typecheck.sh - Run type checking

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Running Mypy type checking..."
echo ""

mypy src/

echo ""
echo "Type checking complete!"
