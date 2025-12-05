# Kepler MCP GitLab Server

A production-ready MCP (Model Context Protocol) server providing GitLab integration tools for AI assistants like Claude Desktop and ChatGPT.

## Features

- **GitLab Integration**: Access GitLab repositories, issues, merge requests, and more through MCP tools
- **OAuth 2.0 Authentication**: GitLab OAuth with PKCE for secure user authentication
- **Multiple Transport Modes**: stdio for local integrations (Claude Desktop), SSE for HTTP-based integrations (ChatGPT custom connectors)
- **Rate Limiting**: Token bucket algorithm for controlling outbound API calls to GitLab
- **Secure Token Storage**: Encrypted token persistence using Fernet symmetric encryption
- **Docker Support**: Multi-stage builds with lint stage for CI validation
- **Comprehensive Testing**: Unit tests, OAuth tests, and integration tests

## Prerequisites

- Python 3.12 or newer
- Docker (optional, for containerized deployment)
- GitLab instance (cloud or self-hosted) with OAuth application configured

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run linting
make lint

# Run type checking
make typecheck

# Run tests
make test

# Run the server in stdio mode
make serve-stdio

# Run the server in SSE mode
make serve-sse
```

### Docker

```bash
# Build and run quality checks
./scripts/build.sh --lint

# Build runtime image
./scripts/build.sh --runtime

# Run the server
./scripts/run.sh --docker --sse
```

## Configuration

Configuration is loaded from (in order of precedence):
1. CLI arguments
2. Environment variables (prefixed with `KEPLER_MCP_`)
3. Configuration file (JSON or YAML)
4. Default values

### Core Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KEPLER_MCP_APP_NAME` | Application name | `Kepler MCP GitLab Server` |
| `KEPLER_MCP_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `KEPLER_MCP_ENVIRONMENT` | Environment (local, dev, stage, prod) | `local` |
| `KEPLER_MCP_TRANSPORT_MODE` | Transport mode (stdio, sse) | `stdio` |
| `KEPLER_MCP_HOST` | Server host (SSE mode) | `0.0.0.0` |
| `KEPLER_MCP_PORT` | Server port (SSE mode) | `8000` |

### GitLab Configuration

| Variable | Description |
|----------|-------------|
| `KEPLER_MCP_GITLAB_URL` | GitLab instance URL (e.g., `https://gitlab.com`) |
| `KEPLER_MCP_GITLAB_API_VERSION` | GitLab API version (default: `v4`) |

### OAuth User Authentication

| Variable | Description |
|----------|-------------|
| `KEPLER_MCP_OAUTH_USER_AUTH_ENABLED` | Enable OAuth user auth |
| `KEPLER_MCP_OAUTH_AUTHORIZATION_URL` | OAuth authorization endpoint |
| `KEPLER_MCP_OAUTH_TOKEN_URL` | OAuth token endpoint |
| `KEPLER_MCP_OAUTH_CLIENT_ID` | OAuth client ID |
| `KEPLER_MCP_OAUTH_CLIENT_SECRET` | OAuth client secret |
| `KEPLER_MCP_OAUTH_REDIRECT_URI` | OAuth callback URL |
| `KEPLER_MCP_OAUTH_SCOPE` | OAuth scopes (space-separated) |

### Token Encryption

| Variable | Description |
|----------|-------------|
| `KEPLER_MCP_TOKEN_ENCRYPTION_KEY` | Fernet encryption key |
| `KEPLER_MCP_TOKEN_STORE_PATH` | Path for persistent token storage |

## GitLab OAuth Setup

1. Create an OAuth application in GitLab:
   - Navigate to User Settings > Applications (or Admin Area > Applications for instance-wide)
   - Name: `Kepler MCP GitLab Server`
   - Redirect URI: `https://your-server.com/oauth/callback`
   - Scopes: `read_api`, `read_user`, `read_repository`
   - Check "Confidential" for server-side applications

2. Configure environment:
   ```bash
   export KEPLER_MCP_OAUTH_USER_AUTH_ENABLED=true
   export KEPLER_MCP_OAUTH_AUTHORIZATION_URL=https://gitlab.example.com/oauth/authorize
   export KEPLER_MCP_OAUTH_TOKEN_URL=https://gitlab.example.com/oauth/token
   export KEPLER_MCP_OAUTH_CLIENT_ID=your_client_id
   export KEPLER_MCP_OAUTH_CLIENT_SECRET=your_client_secret
   export KEPLER_MCP_OAUTH_REDIRECT_URI=https://your-server.com/oauth/callback
   export KEPLER_MCP_OAUTH_SCOPE="read_api read_user read_repository"
   export KEPLER_MCP_GITLAB_URL=https://gitlab.example.com
   ```

## Connecting MCP Clients

### Claude Desktop (stdio)

Add to your Claude Desktop config (`~/.claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "gitlab": {
      "command": "python",
      "args": ["-m", "kepler_mcp_gitlab.cli", "serve", "--transport", "stdio"],
      "env": {
        "KEPLER_MCP_GITLAB_URL": "https://gitlab.example.com",
        "KEPLER_MCP_OAUTH_USER_AUTH_ENABLED": "true"
      }
    }
  }
}
```

### ChatGPT Custom Connector (SSE)

1. Run the server in SSE mode:
   ```bash
   python -m kepler_mcp_gitlab.cli serve --transport sse --host 0.0.0.0 --port 8000
   ```

2. In ChatGPT, add a custom MCP connector:
   - MCP Server URL: `https://your-server.com/sse`
   - Authentication: OAuth (configure as needed)

## Available Tools

The following MCP tools are provided (implement in `src/kepler_mcp_gitlab/application.py`):

- `list_projects` - List GitLab projects accessible to the user
- `get_project` - Get details of a specific project
- `list_issues` - List issues in a project
- `create_issue` - Create a new issue
- `list_merge_requests` - List merge requests in a project
- `get_merge_request` - Get details of a merge request
- `list_pipelines` - List CI/CD pipelines
- `get_file` - Get contents of a file from a repository

## Development

### Running Quality Checks

```bash
# All checks
make check-all

# Individual checks
make lint        # Ruff linting
make typecheck   # Mypy type checking
make test        # Pytest
make coverage    # Pytest with coverage
```

### Helper Scripts

- `scripts/clean.sh` - Remove build artifacts
- `scripts/build.sh` - Build Docker images
- `scripts/run.sh` - Run the server
- `scripts/status.sh` - Check container status
- `scripts/lint.sh` - Run linting
- `scripts/typecheck.sh` - Run type checking
- `scripts/secscan.sh` - Run security scans

## Security

- All tokens are encrypted at rest using Fernet
- PKCE is always used for OAuth flows
- Secrets are redacted in all log output
- Rate limiting prevents API abuse
- Non-root user in Docker containers

## License

MIT License - See [LICENSE](LICENSE) for details.
