# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kepler MCP GitLab Server** - An MCP server providing GitLab integration tools for AI assistants.

This project was created from the `kepler-mcp-server-template` and implements GitLab-specific tools.

## Build and Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Quality checks
make lint              # Ruff linting
make lint-fix          # Ruff with auto-fix
make typecheck         # Mypy strict type checking
make secscan           # Bandit + Safety security scans
make test              # Run all tests
make coverage          # Tests with coverage report
make check-all         # Run all checks in sequence

# Run single test file
pytest tests/test_config.py

# Run single test
pytest tests/test_config.py::TestConfig::test_default_values -v

# Run tests matching pattern
pytest -k "oauth" -v

# Server
make serve-stdio       # Run in stdio mode (Claude Desktop)
make serve-sse         # Run in SSE mode (ChatGPT connectors)

# Docker
make docker-lint       # Build lint stage (CI validation)
make docker-runtime    # Build production image
```

## Architecture Overview

This is an MCP (Model Context Protocol) server template using FastMCP. The architecture supports two transport modes: **stdio** for local integrations and **SSE** for HTTP-based integrations.

### Core Flow

1. **CLI** (`cli.py`) → loads config → creates app via `server.create_app()` → runs transport
2. **server.py** creates FastMCP instance, registers core tools + application tools
3. **transport.py** handles stdio or SSE (Starlette/uvicorn) based on config

### Key Extension Point

**`application.py`** is the primary extension point. To build a specific MCP server (GitLab, JIRA, etc.):
- Implement tools in `register_application_tools(app, config)`
- Extend `Config` model in `config.py` for application-specific fields
- Use `AuthStrategy` from `security.py` for authenticated API calls

### OAuth & Authentication Architecture

Two OAuth flows supported:
- **Authorization Code + PKCE** (`oauth/flows.py`): For user authentication in SSE mode
- **Client Credentials** (`oauth/flows.py`): For service-to-service auth

Authentication strategy pattern in `security.py`:
- `AuthStrategy` (abstract) → `NoAuthStrategy`, `StaticTokenAuthStrategy`, `SessionAuthStrategy`, `ServiceCredentialsAuthStrategy`
- `build_auth_strategy(config, ...)` factory constructs appropriate strategy
- Tools should use strategies via `get_auth_headers()` for API calls

Session flow (SSE mode with OAuth):
1. `/oauth/authorize` → generates PKCE + state → redirects to IdP
2. IdP callback → `/oauth/callback` → exchanges code → stores tokens → creates session
3. SSE requests include session cookie → `SessionManager` retrieves tokens

### Token Storage

- `InMemoryTokenStore`: Development/ephemeral
- `EncryptedFileTokenStore`: Persisted, Fernet-encrypted at rest

### Configuration Precedence

1. CLI arguments (highest)
2. Environment variables (`KEPLER_MCP_*` prefix)
3. Config file (JSON/YAML)
4. Model defaults

## Code Conventions

- Python 3.12+, strict mypy (`strict = true`)
- All functions must have type annotations
- Use `get_logger(__name__)` from `logging_config.py`
- Use `redact()` from `security.py` before logging any potentially sensitive values
- Use `SecretStr` from pydantic for secret config fields
- Async everywhere for I/O operations

## Testing Patterns

- Tests mirror source structure (`tests/oauth/`, `tests/tools/`)
- Use `respx` for mocking HTTP in OAuth tests
- Fixtures in `conftest.py`: `default_config`, `dev_config`, `oauth_config`
- Mark async tests with `@pytest.mark.asyncio` (auto mode enabled)
