# Kepler MCP GitLab Server

A production-ready MCP (Model Context Protocol) server providing GitLab integration tools for AI assistants like Claude Desktop and ChatGPT.

## How It Works

This MCP server acts as a bridge between AI assistants (ChatGPT, Claude, etc.) and your GitLab instance. Users authenticate via GitLab OAuth - just like connecting any third-party app.

```
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│   AI Assistant  │      │   MCP Server        │      │    GitLab       │
│   (ChatGPT,     │◄────►│   (Your Company     │◄────►│    (Your        │
│    Claude)      │      │    Hosted)          │      │    Instance)    │
└─────────────────┘      └─────────────────────┘      └─────────────────┘
        │                         │                          │
        │    1. User connects     │                          │
        │    ─────────────────►   │                          │
        │                         │   2. Redirect to GitLab  │
        │                         │   ─────────────────────► │
        │                         │                          │
        │                         │   3. User authorizes     │
        │                         │   ◄───────────────────── │
        │                         │                          │
        │    4. Connected!        │   5. API calls with      │
        │    ◄─────────────────   │      user's permissions  │
        │                         │   ◄────────────────────► │
```

**For end users**: Simply add the MCP server URL to their AI assistant and authorize with GitLab. No tokens or configuration needed.

**For administrators**: One-time setup to deploy the server and register the OAuth application with GitLab.

## Features

- **GitLab Integration**: Access projects, issues, merge requests, and more through MCP tools
- **OAuth 2.0 Authentication**: Users authorize via GitLab - no tokens to manage
- **Per-User Permissions**: Each user's GitLab permissions are respected
- **Multiple Transport Modes**: stdio for local (Claude Desktop), SSE for HTTP (ChatGPT)
- **Secure Token Storage**: Encrypted session storage using Fernet encryption
- **Docker Support**: Production-ready container images

## Available Tools

Once connected, users can ask their AI assistant to:

| Tool | Description |
|------|-------------|
| **Projects** | |
| `list_projects` | List accessible GitLab projects |
| `get_project` | Get project details |
| `search_projects` | Search for projects |
| `get_project_languages` | Get language breakdown |
| **Issues** | |
| `list_issues` | List issues in a project |
| `get_issue` | Get issue details |
| `create_issue` | Create a new issue |
| `update_issue` | Update an issue |
| `close_issue` / `reopen_issue` | Change issue state |
| `list_issue_comments` | List comments on an issue |
| `add_issue_comment` | Add a comment |
| **Merge Requests** | |
| `list_merge_requests` | List MRs in a project |
| `get_merge_request` | Get MR details |
| `create_merge_request` | Create a new MR |
| `update_merge_request` | Update an MR |
| `merge_merge_request` | Merge an MR |
| `approve_merge_request` | Approve an MR |
| `get_merge_request_changes` | Get MR diff |
| `list_merge_request_discussions` | List review threads |
| **Repository** | |
| `list_branches` | List repository branches |
| `get_branch` | Get branch details |
| `create_branch` | Create a new branch |
| `delete_branch` | Delete a branch |
| `list_tags` | List repository tags |
| `get_tag` | Get tag details |
| `create_tag` | Create a new tag |
| `delete_tag` | Delete a tag |
| `compare_branches` | Compare two branches/commits |
| `list_repository_tree` | List files and directories |
| `get_file` | Get file metadata |
| `get_file_content` | Get file contents (decoded) |
| `create_file` | Create a new file |
| `update_file` | Update an existing file |
| `delete_file` | Delete a file |
| `get_file_blame` | Get file blame/history |
| `list_commits` | List repository commits |
| `get_commit` | Get commit details |
| `get_commit_diff` | Get commit diff |
| `cherry_pick_commit` | Cherry-pick a commit |
| `get_commit_refs` | Get refs containing a commit |
| **Utilities** | |
| `get_current_user` | Get authenticated user info |
| `get_gitlab_config` | Get server configuration |

---

# Deployment Guide (For Administrators)

This section is for IT administrators deploying the MCP server for their organization.

## Prerequisites

- Python 3.12+ or Docker
- Access to your GitLab instance (admin or ability to create OAuth applications)
- A server/host to run the MCP server (can be the same as GitLab or separate)

## Understanding OAuth Application Credentials

When you deploy this server, you need to register it as an OAuth application with GitLab. This is similar to how Slack, GitHub, or any third-party integration works.

**Why?** GitLab needs to know:
1. **Who is asking** (Client ID) - Identifies your MCP server
2. **That it's really you** (Client Secret) - Proves the request is legitimate
3. **Where to send users back** (Redirect URI) - After they authorize

These are **application credentials**, not user credentials. You set them up once, and then all users in your organization can connect without any additional configuration.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OAuth Flow Explained                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. User clicks "Connect to GitLab" in ChatGPT                      │
│                          │                                           │
│                          ▼                                           │
│  2. MCP Server redirects to GitLab:                                 │
│     gitlab.com/oauth/authorize?client_id=ABC123&...                 │
│                          │                                           │
│                          │  ◄── GitLab checks: "Is ABC123 a valid   │
│                          │       registered application?"            │
│                          ▼                                           │
│  3. User sees GitLab login page, then:                              │
│     "Kepler MCP Server wants to access your account"                │
│     [Authorize] [Deny]                                              │
│                          │                                           │
│                          ▼                                           │
│  4. User clicks Authorize, GitLab redirects back with temp code     │
│                          │                                           │
│                          ▼                                           │
│  5. MCP Server exchanges code for tokens:                           │
│     POST gitlab.com/oauth/token                                     │
│     { client_id: ABC123, client_secret: XYZ789, code: ... }         │
│                          │                                           │
│                          │  ◄── GitLab verifies the secret matches  │
│                          │       the registered application          │
│                          ▼                                           │
│  6. GitLab returns access token, user is connected!                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Step 1: Register OAuth Application in GitLab

1. Log into your GitLab instance as an admin (or any user for user-level apps)

2. Navigate to:
   - **Instance-wide** (recommended): Admin Area → Applications
   - **User-level**: User Settings → Applications

3. Click **New Application** and fill in:

   | Field | Value |
   |-------|-------|
   | **Name** | `Kepler MCP GitLab Server` |
   | **Redirect URI** | `https://your-mcp-server.com/oauth/callback` |
   | **Confidential** | ✅ Yes (checked) |
   | **Scopes** | ✅ `api` ✅ `read_user` ✅ `read_repository` |

4. Click **Save application**

5. **Copy and securely store**:
   - **Application ID** (Client ID)
   - **Secret** (Client Secret) - shown only once!

## Step 2: Configure the Server

Create a configuration file or set environment variables:

### Option A: Environment Variables

```bash
# Required: GitLab Instance
export KEPLER_MCP_GITLAB_URL=https://gitlab.your-company.com

# Required: OAuth Application Credentials (from Step 1)
export KEPLER_MCP_OAUTH_USER_AUTH_ENABLED=true
export KEPLER_MCP_OAUTH_CLIENT_ID=your_application_id_here
export KEPLER_MCP_OAUTH_CLIENT_SECRET=your_secret_here
export KEPLER_MCP_OAUTH_REDIRECT_URI=https://your-mcp-server.com/oauth/callback
export KEPLER_MCP_OAUTH_SCOPE="api read_user read_repository"

# Required: OAuth Endpoints (adjust domain for your GitLab)
export KEPLER_MCP_OAUTH_AUTHORIZATION_URL=https://gitlab.your-company.com/oauth/authorize
export KEPLER_MCP_OAUTH_TOKEN_URL=https://gitlab.your-company.com/oauth/token
export KEPLER_MCP_OAUTH_USERINFO_URL=https://gitlab.your-company.com/api/v4/user

# Server Settings
export KEPLER_MCP_TRANSPORT_MODE=sse
export KEPLER_MCP_HOST=0.0.0.0
export KEPLER_MCP_PORT=8000

# Optional: Token Encryption (recommended for production)
# Generate key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
export KEPLER_MCP_TOKEN_ENCRYPTION_KEY=your_generated_fernet_key
export KEPLER_MCP_TOKEN_STORE_PATH=/var/lib/kepler-mcp/tokens.json
```

### Option B: `.env` File

Create a `.env` file in the project root with the same variables (without `export`).

### GitLab.com vs Self-Hosted

| Setting | GitLab.com | Self-Hosted |
|---------|-----------|-------------|
| `GITLAB_URL` | `https://gitlab.com` | `https://gitlab.your-company.com` |
| `OAUTH_AUTHORIZATION_URL` | `https://gitlab.com/oauth/authorize` | `https://gitlab.your-company.com/oauth/authorize` |
| `OAUTH_TOKEN_URL` | `https://gitlab.com/oauth/token` | `https://gitlab.your-company.com/oauth/token` |
| `OAUTH_USERINFO_URL` | `https://gitlab.com/api/v4/user` | `https://gitlab.your-company.com/api/v4/user` |

## Step 3: Deploy the Server

### Option A: Direct Python

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install
pip install -e .

# Run
python -m kepler_mcp_gitlab.cli serve --transport sse
```

### Option B: Docker

```bash
# Build
docker build -t kepler-mcp-gitlab -f docker/Dockerfile .

# Run
docker run -d \
  --name kepler-mcp-gitlab \
  -p 8000:8000 \
  -e KEPLER_MCP_GITLAB_URL=https://gitlab.your-company.com \
  -e KEPLER_MCP_OAUTH_USER_AUTH_ENABLED=true \
  -e KEPLER_MCP_OAUTH_CLIENT_ID=your_client_id \
  -e KEPLER_MCP_OAUTH_CLIENT_SECRET=your_secret \
  -e KEPLER_MCP_OAUTH_REDIRECT_URI=https://your-mcp-server.com/oauth/callback \
  -e KEPLER_MCP_OAUTH_AUTHORIZATION_URL=https://gitlab.your-company.com/oauth/authorize \
  -e KEPLER_MCP_OAUTH_TOKEN_URL=https://gitlab.your-company.com/oauth/token \
  -e KEPLER_MCP_OAUTH_SCOPE="api read_user read_repository" \
  kepler-mcp-gitlab
```

### Option C: Docker Compose

```yaml
version: '3.8'
services:
  mcp-gitlab:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      KEPLER_MCP_GITLAB_URL: https://gitlab.your-company.com
      KEPLER_MCP_OAUTH_USER_AUTH_ENABLED: "true"
      KEPLER_MCP_OAUTH_CLIENT_ID: ${OAUTH_CLIENT_ID}
      KEPLER_MCP_OAUTH_CLIENT_SECRET: ${OAUTH_CLIENT_SECRET}
      KEPLER_MCP_OAUTH_REDIRECT_URI: https://your-mcp-server.com/oauth/callback
      KEPLER_MCP_OAUTH_AUTHORIZATION_URL: https://gitlab.your-company.com/oauth/authorize
      KEPLER_MCP_OAUTH_TOKEN_URL: https://gitlab.your-company.com/oauth/token
      KEPLER_MCP_OAUTH_SCOPE: "api read_user read_repository"
    restart: unless-stopped
```

## Step 4: Verify Deployment

```bash
# Health check
curl https://your-mcp-server.com/health

# Expected response:
# {"status": "ok", "app_name": "Kepler MCP GitLab Server", "environment": "prod"}

# Test OAuth redirect (should redirect to GitLab)
curl -I https://your-mcp-server.com/oauth/authorize

# Expected: HTTP 302 with Location header pointing to GitLab
```

## Step 5: Inform Your Users

Once deployed, share these instructions with your users:

> **Connecting to GitLab from ChatGPT**
>
> 1. In ChatGPT, go to Settings → Connections → Add MCP Server
> 2. Enter the server URL: `https://your-mcp-server.com/sse`
> 3. Click Connect - you'll be redirected to GitLab
> 4. Log in to GitLab and click "Authorize"
> 5. Done! You can now ask ChatGPT about your GitLab projects.
>
> Try: "List my GitLab projects" or "Show open issues in project X"

---

# Configuration Reference

## All Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| **Core** | | | |
| `KEPLER_MCP_APP_NAME` | Application name | `Kepler MCP GitLab Server` | No |
| `KEPLER_MCP_LOG_LEVEL` | Log level | `INFO` | No |
| `KEPLER_MCP_ENVIRONMENT` | Environment (local/dev/stage/prod) | `local` | No |
| `KEPLER_MCP_TRANSPORT_MODE` | Transport (stdio/sse) | `stdio` | No |
| `KEPLER_MCP_HOST` | Server bind host | `0.0.0.0` | No |
| `KEPLER_MCP_PORT` | Server bind port | `8000` | No |
| **GitLab** | | | |
| `KEPLER_MCP_GITLAB_URL` | GitLab instance URL | `https://gitlab.com` | Yes |
| **OAuth** (required for SSE mode) | | | |
| `KEPLER_MCP_OAUTH_USER_AUTH_ENABLED` | Enable OAuth | `false` | Yes* |
| `KEPLER_MCP_OAUTH_CLIENT_ID` | OAuth Client ID | - | Yes* |
| `KEPLER_MCP_OAUTH_CLIENT_SECRET` | OAuth Client Secret | - | Yes* |
| `KEPLER_MCP_OAUTH_AUTHORIZATION_URL` | OAuth authorize endpoint | - | Yes* |
| `KEPLER_MCP_OAUTH_TOKEN_URL` | OAuth token endpoint | - | Yes* |
| `KEPLER_MCP_OAUTH_REDIRECT_URI` | OAuth callback URL | - | Yes* |
| `KEPLER_MCP_OAUTH_SCOPE` | OAuth scopes | - | Yes* |
| `KEPLER_MCP_OAUTH_USERINFO_URL` | User info endpoint | - | No |
| **Token Storage** | | | |
| `KEPLER_MCP_TOKEN_ENCRYPTION_KEY` | Fernet key for encryption | - | No** |
| `KEPLER_MCP_TOKEN_STORE_PATH` | Path for token persistence | - | No** |
| **Rate Limiting** | | | |
| `KEPLER_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE` | Max requests/min | `60` | No |
| `KEPLER_MCP_RATE_LIMIT_BURST` | Burst size | `10` | No |

\* Required when `OAUTH_USER_AUTH_ENABLED=true`
\** Required together if persistent sessions are needed

---

# Development

## Setup

```bash
# Clone and setup
git clone <repo>
cd kepler-mcp-gitlab-server

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Quality Checks

```bash
make lint        # Ruff linting
make typecheck   # Mypy type checking
make test        # Run tests
make coverage    # Tests with coverage report
make check-all   # All checks
```

## Project Structure

```
src/kepler_mcp_gitlab/
├── cli.py              # Command-line interface
├── server.py           # FastMCP server setup
├── config.py           # Configuration management
├── context.py          # Request context and session management
├── application.py      # Tool registration
├── transport.py        # stdio/SSE transport handlers
├── security.py         # Auth strategies, token handling
├── gitlab/
│   ├── client.py       # GitLab API client
│   └── exceptions.py   # GitLab-specific errors
├── oauth/
│   ├── flows.py        # OAuth flow implementations
│   ├── pkce.py         # PKCE support
│   ├── session.py      # Session management
│   └── token_store.py  # Token persistence
└── tools/
    ├── projects.py     # Project tools
    ├── issues.py       # Issue tools
    ├── merge_requests.py # MR tools
    └── repository.py   # Repository tools (branches, tags, files, commits)
```

---

# Security

- **OAuth 2.0 with PKCE**: Industry-standard secure authentication
- **No stored passwords**: Users authenticate directly with GitLab
- **Per-user permissions**: Each user's GitLab access rights are respected
- **Encrypted tokens**: Session tokens encrypted at rest with Fernet
- **Secret redaction**: Sensitive values never appear in logs
- **Non-root containers**: Docker images run as unprivileged user

---

# Troubleshooting

## OAuth Errors

**"Invalid redirect URI"**
- Ensure the redirect URI in GitLab exactly matches your server's callback URL
- Check for trailing slashes, http vs https

**"Invalid client"**
- Verify Client ID is correct
- Check if the OAuth application is still active in GitLab

**"Invalid state"**
- State expired (default 10 min) - try the flow again
- Server may have restarted during the OAuth flow

## Connection Issues

**Health check fails**
```bash
# Check if server is running
curl http://localhost:8000/health

# Check logs
docker logs kepler-mcp-gitlab
```

**GitLab API errors**
```bash
# Test GitLab connectivity directly
curl -H "Authorization: Bearer <token>" https://gitlab.your-company.com/api/v4/user
```

---

# License

MIT License - See [LICENSE](LICENSE) for details.
