#!/bin/bash
# scripts/secscan.sh - Run security scans

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

BANDIT_EXIT=0
SAFETY_EXIT=0

echo "Security Scanning"
echo "================="
echo ""

# Run Bandit
echo "Running Bandit security analysis..."
echo "-----------------------------------"
if bandit -r src/; then
    echo "Bandit: PASSED"
else
    BANDIT_EXIT=1
    echo "Bandit: FAILED"
fi
echo ""

# Run Safety
echo "Running Safety dependency check..."
echo "----------------------------------"
if safety check --full-report; then
    echo "Safety: PASSED"
else
    SAFETY_EXIT=1
    echo "Safety: FAILED"
fi
echo ""

# Summary
echo "Summary"
echo "======="
if [[ $BANDIT_EXIT -eq 0 ]]; then
    echo "  Bandit: PASSED"
else
    echo "  Bandit: FAILED"
fi

if [[ $SAFETY_EXIT -eq 0 ]]; then
    echo "  Safety: PASSED"
else
    echo "  Safety: FAILED"
fi
echo ""

# Exit with failure if any tool failed
if [[ $BANDIT_EXIT -ne 0 || $SAFETY_EXIT -ne 0 ]]; then
    echo "Security scan FAILED!"
    exit 1
fi

echo "Security scan complete!"
