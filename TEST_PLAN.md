# GitLab MCP Server - Testing Guide

This document explains how the MCP server works and provides step-by-step testing instructions.

## Table of Contents

1. [Understanding the Architecture](#understanding-the-architecture)
2. [Prerequisites](#prerequisites)
3. [GitLab OAuth Application Setup](#gitlab-oauth-application-setup)
4. [Environment Configuration](#environment-configuration)
5. [Build and Run](#build-and-run)
6. [Manual Testing with Python Script](#manual-testing-with-python-script)
7. [Test Checklist](#test-checklist)
8. [Troubleshooting](#troubleshooting)

---

## Understanding the Architecture

### How MCP + OAuth Works

This server uses the **Model Context Protocol (MCP)** to expose GitLab tools to AI assistants. It uses **OAuth 2.0** for authentication, so users authorize via GitLab rather than managing tokens manually.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REAL MCP CLIENT FLOW                               │
│                     (ChatGPT, Claude Desktop, etc.)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐        ┌─────────────────┐        ┌─────────────┐         │
│  │  MCP Client │        │   MCP Server    │        │   GitLab    │         │
│  │  (ChatGPT)  │        │  (This Server)  │        │             │         │
│  └──────┬──────┘        └────────┬────────┘        └──────┬──────┘         │
│         │                        │                        │                 │
│    1.   │  User clicks           │                        │                 │
│         │  "Connect to GitLab"   │                        │                 │
│         │                        │                        │                 │
│    2.   │  GET /oauth/authorize  │                        │                 │
│         │───────────────────────►│                        │                 │
│         │                        │                        │                 │
│    3.   │  302 Redirect          │                        │                 │
│         │◄───────────────────────│                        │                 │
│         │                        │                        │                 │
│    4.   │  Browser opens GitLab login/authorize page      │                 │
│         │────────────────────────────────────────────────►│                 │
│         │                        │                        │                 │
│    5.   │  User clicks "Authorize"                        │                 │
│         │◄────────────────────────────────────────────────│                 │
│         │                        │                        │                 │
│    6.   │  Callback: /oauth/callback?code=xxx&state=yyy   │                 │
│         │───────────────────────►│                        │                 │
│         │                        │                        │                 │
│    7.   │                        │  Exchange code for     │                 │
│         │                        │  access token          │                 │
│         │                        │───────────────────────►│                 │
│         │                        │◄───────────────────────│                 │
│         │                        │                        │                 │
│    8.   │  Set-Cookie: session_id=xxx                     │                 │
│         │◄───────────────────────│                        │                 │
│         │                        │                        │                 │
│   ┌─────┴─────────────────────────────────────────────────┴─────┐           │
│   │  CLIENT AUTOMATICALLY STORES THE SESSION COOKIE             │           │
│   └─────┬─────────────────────────────────────────────────┬─────┘           │
│         │                        │                        │                 │
│    9.   │  GET /sse              │                        │                 │
│         │  Cookie: session_id=xxx│                        │                 │
│         │───────────────────────►│                        │                 │
│         │                        │                        │                 │
│   10.   │  SSE connection open   │                        │                 │
│         │◄──────────────────────►│                        │                 │
│         │                        │                        │                 │
│   11.   │  POST /messages        │  GitLab API calls      │                 │
│         │  (MCP tool calls)      │  (with user's token)   │                 │
│         │───────────────────────►│───────────────────────►│                 │
│         │◄───────────────────────│◄───────────────────────│                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Concepts

| Term | Description |
|------|-------------|
| **MCP Client** | An AI assistant (ChatGPT, Claude) that connects to MCP servers |
| **MCP Server** | This application - exposes GitLab tools via MCP protocol |
| **OAuth Flow** | User authorizes the MCP server to access GitLab on their behalf |
| **Session Cookie** | After OAuth, a `session_id` cookie links requests to the user's GitLab tokens |
| **SSE Transport** | Server-Sent Events - how MCP clients communicate over HTTP |
| **Transport Session** | FastMCP's internal session ID (different from OAuth session) |

### Why Manual Testing Requires Extra Steps

Real MCP clients (ChatGPT, Claude Desktop) handle the OAuth flow automatically:

1. They open a browser/popup for authorization
2. They intercept the callback
3. They store and send the session cookie automatically

When testing manually with curl or Python scripts, **you** must handle what the MCP client would do automatically:

1. Complete OAuth in a browser
2. Get the session ID from the response
3. Include it as a cookie in subsequent requests

---

## Prerequisites

### Required Software

- Python 3.12+
- Access to a GitLab instance (self-hosted or gitlab.com)
- GitLab account with permissions to create OAuth applications
- A web browser for OAuth testing

### Verify Prerequisites

```bash
python3.12 --version  # Should be 3.12+
```

---

## GitLab OAuth Application Setup

### Step 1: Create OAuth Application in GitLab

1. Navigate to your GitLab instance
2. Go to **User Settings** → **Applications**
3. Click **Add new application**
4. Fill in the form:

| Field | Value |
|-------|-------|
| **Name** | `Kepler MCP GitLab Server (Dev)` |
| **Redirect URI** | `http://<your-server-ip>:8000/oauth/callback` |
| **Confidential** | ✅ Checked |
| **Scopes** | ✅ `api` ✅ `read_user` ✅ `read_repository` |

**Important:** The redirect URI must match exactly what you configure in `.env`.

1. Click **Save application**
2. **Copy and save:**
   - **Application ID** (Client ID)
   - **Secret** (Client Secret) - shown only once!

---

## Environment Configuration

### Create `.env` File

```bash
cd /path/to/kepler-mcp-gitlab-server
```

Create a `.env` file with these values:

```bash
# Application Settings
KEPLER_MCP_APP_NAME="Kepler MCP Server"
KEPLER_MCP_LOG_LEVEL=DEBUG
KEPLER_MCP_ENVIRONMENT=local

# Server Settings
KEPLER_MCP_TRANSPORT_MODE=sse
KEPLER_MCP_HOST=0.0.0.0
KEPLER_MCP_PORT=8000

# GitLab Instance
KEPLER_MCP_GITLAB_URL=https://gitlab.your-company.com

# OAuth Configuration (REQUIRED)
KEPLER_MCP_OAUTH_USER_AUTH_ENABLED=true
KEPLER_MCP_OAUTH_CLIENT_ID=<your-application-id>
KEPLER_MCP_OAUTH_CLIENT_SECRET=<your-secret>
KEPLER_MCP_OAUTH_REDIRECT_URI=http://<your-server-ip>:8000/oauth/callback
KEPLER_MCP_OAUTH_SCOPE=api read_user read_repository

# OAuth Endpoints (adjust for your GitLab instance)
KEPLER_MCP_OAUTH_AUTHORIZATION_URL=https://gitlab.your-company.com/oauth/authorize
KEPLER_MCP_OAUTH_TOKEN_URL=https://gitlab.your-company.com/oauth/token
KEPLER_MCP_OAUTH_USERINFO_URL=https://gitlab.your-company.com/api/v4/user
```

**Note:** Replace `<your-server-ip>` with the actual IP or hostname where the MCP server runs. This must match what you configured in GitLab.

---

## Build and Run

### Step 1: Set Up Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -e ".[dev]"
```

### Step 3: Run Tests (Optional)

```bash
make lint   # Linting
make test   # Unit tests (160 tests)
```

### Step 4: Start the Server

```bash
python -m kepler_mcp_gitlab.cli serve --transport sse
```

**Expected Output:**
```
INFO | Starting Kepler MCP Server (app: Kepler MCP Server, env: local, transport: sse)
INFO | OAuth user authentication enabled
INFO | Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 5: Verify Server is Running

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status":"ok","app_name":"Kepler MCP Server","environment":"local"}
```

---

## Manual Testing with Python Script

Since we're not using a real MCP client, we need to manually handle the OAuth flow. Here's the step-by-step process:

### Step 1: Install MCP Client Library

```bash
pip install mcp httpx
```

### Step 2: Create Test Script

Save this as `test_mcp.py`:

```python
"""MCP GitLab Server - Manual OAuth Test Script

This script tests the MCP server by:
1. Starting OAuth flow (you authorize in browser)
2. Capturing the session ID from the callback response
3. Using the session to call MCP tools
"""
import asyncio
import json
import urllib.parse
import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

# Update this to match your server
BASE_URL = "http://localhost:8000"


async def start_oauth():
    """Get the OAuth authorization URL."""
    async with httpx.AsyncClient(follow_redirects=False) as client:
        resp = await client.get(f"{BASE_URL}/oauth/authorize")
        if resp.status_code == 302:
            return resp.headers.get("location")
    return None


async def complete_oauth(callback_url: str) -> str | None:
    """Exchange callback URL for session ID."""
    parsed = urllib.parse.urlparse(callback_url)
    params = urllib.parse.parse_qs(parsed.query)

    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]

    if not code or not state:
        print("ERROR: Could not parse code/state from URL")
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/oauth/callback",
            params={"code": code, "state": state}
        )

        if resp.status_code == 200:
            data = resp.json()
            # In local environment, session_id is in the response body
            return data.get("session_id")

    return None


async def test_mcp_tools(session_id: str):
    """Test MCP tools with authenticated session."""
    headers = {"Cookie": f"session_id={session_id}"}

    async with sse_client(f"{BASE_URL}/sse", headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✓ Connected to MCP server!")

            # Test get_current_user
            print("\nTesting get_current_user...")
            result = await session.call_tool("get_current_user", {})
            for item in result.content:
                if hasattr(item, "text"):
                    data = json.loads(item.text)
                    print(f"  Username: {data.get('username')}")
                    print(f"  Name: {data.get('name')}")

            # Test list_projects
            print("\nTesting list_projects...")
            result = await session.call_tool("list_projects", {"per_page": 5})
            for item in result.content:
                if hasattr(item, "text"):
                    data = json.loads(item.text)
                    if isinstance(data, list):
                        print(f"  Found {len(data)} projects:")
                        for proj in data[:5]:
                            print(f"    - {proj.get('path_with_namespace')}")


async def main():
    import sys

    if len(sys.argv) > 1:
        # Session ID or callback URL provided
        arg = sys.argv[1]
        if arg.startswith("http"):
            session_id = await complete_oauth(arg)
        else:
            session_id = arg

        if session_id:
            await test_mcp_tools(session_id)
        return

    # Interactive flow
    print("=" * 60)
    print("MCP GitLab Server - OAuth Test")
    print("=" * 60)

    auth_url = await start_oauth()
    if not auth_url:
        print("ERROR: Failed to get authorization URL")
        return

    print("\n1. Open this URL in your browser:\n")
    print(f"   {auth_url}\n")
    print("2. Authorize with GitLab")
    print("3. Copy the FULL URL from your browser after authorization")
    print("   (starts with your callback URL)")
    print("=" * 60)

    callback_url = input("\nPaste the callback URL: ").strip()

    session_id = await complete_oauth(callback_url)
    if session_id:
        print(f"\n✓ Got session ID: {session_id[:16]}...")
        await test_mcp_tools(session_id)
    else:
        print("\nERROR: Failed to get session ID")


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Run the Test

```bash
python test_mcp.py
```

### Step 4: Follow the Prompts

1. The script displays a GitLab authorization URL
2. Open that URL in your browser
3. Log in to GitLab and click **Authorize**
4. After authorization, you'll see a JSON response in the browser
5. Copy the **full URL** from your browser's address bar
6. Paste it back into the script

### Step 5: Verify Results

Expected output after successful authentication:

```text
✓ Connected to MCP server!

Testing get_current_user...
  Username: your_username
  Name: Your Name

Testing list_projects...
  Found 5 projects:
    - group/project-1
    - group/project-2
    ...
```

---

## Test Checklist

### Server Startup

- [ ] Server starts without errors
- [ ] Health endpoint returns `{"status": "ok"}`
- [ ] OAuth endpoints are registered (`/oauth/authorize`, `/oauth/callback`)

### OAuth Flow

- [ ] `/oauth/authorize` redirects to GitLab
- [ ] GitLab shows authorization page with correct app name
- [ ] Clicking "Authorize" redirects back to callback URL
- [ ] Callback returns JSON with `session_id` (in local environment)

### MCP Tools (after authentication)

- [ ] `get_current_user` returns your GitLab user info
- [ ] `list_projects` returns projects you have access to
- [ ] `get_gitlab_config` returns server configuration

### Error Handling

- [ ] Invalid session returns 401 error
- [ ] Invalid project ID returns appropriate error
- [ ] Expired sessions are handled gracefully

---

## Troubleshooting

### "Invalid redirect URI" Error

The redirect URI in your `.env` must **exactly** match what's configured in GitLab:

- Check for trailing slashes
- Check http vs https
- Check the IP/hostname matches

### "Invalid state" Error

The OAuth state expired (default 10 minutes). Start the flow again.

### Session Not Found / 401 Errors

1. Make sure you're using the **full** session ID (64 characters), not the truncated log display (8 characters)
2. The session may have expired (24 hour default)
3. Server restart clears in-memory sessions

### Server Won't Start

```bash
# Check for port conflicts
lsof -i :8000

# Check configuration
grep OAUTH .env | grep -v SECRET
```

### GitLab API Errors

Check that:

1. OAuth scopes include `api`, `read_user`, `read_repository`
2. Your GitLab user has access to the projects you're querying
3. The GitLab URL is correct

---

## Test Summary

| Category | Test | Status |
|----------|------|--------|
| Server | Health check responds | [ ] |
| Server | Server logs show OAuth enabled | [ ] |
| OAuth | /oauth/authorize redirects to GitLab | [ ] |
| OAuth | Authorization completes successfully | [ ] |
| OAuth | Session ID returned in response | [ ] |
| MCP | SSE connection established | [ ] |
| MCP | get_current_user returns user info | [ ] |
| MCP | list_projects returns projects | [ ] |

**Tester:** _____________________
**Date:** _____________________
**GitLab Instance:** _____________________
