#!/bin/bash
# scripts/run.sh - Run the MCP server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

TRANSPORT="sse"
PORT="8000"
HOST="0.0.0.0"
ENV_VARS=()
USE_DOCKER=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stdio)
            TRANSPORT="stdio"
            shift
            ;;
        --sse)
            TRANSPORT="sse"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        -e|--env)
            ENV_VARS+=("-e" "$2")
            shift 2
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --stdio       Run in stdio mode (default: sse)"
            echo "  --sse         Run in SSE mode (default)"
            echo "  --port PORT   Port for SSE mode (default: 8000)"
            echo "  --host HOST   Host for SSE mode (default: 0.0.0.0)"
            echo "  -e, --env VAR=VALUE  Set environment variable"
            echo "  --docker      Run in Docker container"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ "$USE_DOCKER" == true ]]; then
    echo "Running MCP server in Docker container..."
    echo "  Transport: $TRANSPORT"

    if [[ "$TRANSPORT" == "sse" ]]; then
        echo "  Host: $HOST"
        echo "  Port: $PORT"
        echo ""
        docker run --rm -it \
            -p "${PORT}:8000" \
            "${ENV_VARS[@]}" \
            -e "KEPLER_MCP_TRANSPORT_MODE=$TRANSPORT" \
            kepler-mcp-gitlab:latest
    else
        echo ""
        docker run --rm -it \
            "${ENV_VARS[@]}" \
            -e "KEPLER_MCP_TRANSPORT_MODE=$TRANSPORT" \
            kepler-mcp-gitlab:latest \
            python -m kepler_mcp_gitlab.cli serve --transport stdio
    fi
else
    echo "Running MCP server locally..."
    echo "  Transport: $TRANSPORT"

    if [[ "$TRANSPORT" == "sse" ]]; then
        echo "  Host: $HOST"
        echo "  Port: $PORT"
        echo ""
        echo "Server URL: http://${HOST}:${PORT}/sse"
        echo ""
        python -m kepler_mcp_gitlab.cli serve --transport sse --host "$HOST" --port "$PORT"
    else
        echo ""
        python -m kepler_mcp_gitlab.cli serve --transport stdio
    fi
fi
