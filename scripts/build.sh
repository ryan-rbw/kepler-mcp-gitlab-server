#!/bin/bash
# scripts/build.sh - Build Docker images for the MCP server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

BUILD_LINT=false
BUILD_RUNTIME=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --lint)
            BUILD_LINT=true
            shift
            ;;
        --runtime)
            BUILD_RUNTIME=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --lint      Build only the lint stage"
            echo "  --runtime   Build only the runtime stage"
            echo "  -h, --help  Show this help message"
            echo ""
            echo "If no options are provided, both stages are built."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default to building both if no flags specified
if [[ "$BUILD_LINT" == false && "$BUILD_RUNTIME" == false ]]; then
    BUILD_LINT=true
    BUILD_RUNTIME=true
fi

if [[ "$BUILD_LINT" == true ]]; then
    echo "Building lint stage..."
    docker build --target lint -t kepler-mcp-gitlab:lint -f docker/Dockerfile .
    echo "Lint stage built: kepler-mcp-gitlab:lint"
    echo ""
fi

if [[ "$BUILD_RUNTIME" == true ]]; then
    echo "Building runtime stage..."
    docker build --target runtime -t kepler-mcp-gitlab:latest -f docker/Dockerfile .
    echo "Runtime stage built: kepler-mcp-gitlab:latest"
    echo ""
fi

echo "Build complete!"
echo ""
echo "Available images:"
docker images kepler-mcp-gitlab --format "  {{.Repository}}:{{.Tag}} ({{.Size}})"
