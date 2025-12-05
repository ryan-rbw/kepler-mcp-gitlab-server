#!/bin/bash
# scripts/status.sh - Check MCP server container status

set -e

CONTAINER_NAME="kepler-mcp-gitlab"

echo "MCP Server Status"
echo "================="
echo ""

# Check if any kepler-mcp-gitlab containers are running
RUNNING_CONTAINERS=$(docker ps --filter "ancestor=kepler-mcp-gitlab:latest" --format "{{.ID}}" 2>/dev/null || true)

if [[ -z "$RUNNING_CONTAINERS" ]]; then
    # Check if container exists but is stopped
    STOPPED_CONTAINERS=$(docker ps -a --filter "ancestor=kepler-mcp-gitlab:latest" --format "{{.ID}}" 2>/dev/null || true)

    if [[ -z "$STOPPED_CONTAINERS" ]]; then
        echo "Status: NOT FOUND"
        echo "No kepler-mcp-gitlab containers exist."
        echo ""
        echo "To start the server, run:"
        echo "  ./scripts/run.sh --docker"
        exit 1
    else
        echo "Status: STOPPED"
        echo ""
        echo "Stopped containers:"
        docker ps -a --filter "ancestor=kepler-mcp-gitlab:latest" --format "table {{.ID}}\t{{.Status}}\t{{.CreatedAt}}"
        exit 1
    fi
fi

echo "Status: RUNNING"
echo ""

# Show container details
echo "Container Details:"
docker ps --filter "ancestor=kepler-mcp-gitlab:latest" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Show port bindings
echo "Port Bindings:"
for container_id in $RUNNING_CONTAINERS; do
    ports=$(docker port "$container_id" 2>/dev/null || echo "No port mappings")
    echo "  Container $container_id: $ports"
done
echo ""

# Show last 10 log lines
echo "Recent Logs (last 10 lines):"
echo "----------------------------"
for container_id in $RUNNING_CONTAINERS; do
    docker logs --tail 10 "$container_id" 2>&1 | sed 's/^/  /'
done
echo ""

# Health check (if endpoint is available)
CONTAINER_PORT=$(docker ps --filter "ancestor=kepler-mcp-gitlab:latest" --format "{{.Ports}}" | grep -oP '0\.0\.0\.0:\K[0-9]+' | head -1)
if [[ -n "$CONTAINER_PORT" ]]; then
    echo "Health Check:"
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${CONTAINER_PORT}/health" 2>/dev/null | grep -q "200"; then
        echo "  Endpoint http://localhost:${CONTAINER_PORT}/health: OK"
    else
        echo "  Endpoint http://localhost:${CONTAINER_PORT}/health: NOT RESPONDING"
    fi
fi

exit 0
