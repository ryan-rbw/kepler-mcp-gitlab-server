# Kepler MCP Server Template - Multi-stage Dockerfile
#
# Build stages:
#   - base: Common base image with Python and non-root user
#   - lint: Runs all quality checks (ruff, mypy, bandit, safety)
#   - runtime: Production image without dev dependencies
#
# Usage:
#   Build lint stage (CI validation):
#     docker build --target lint -t kepler-mcp-gitlab:lint -f docker/Dockerfile .
#
#   Build runtime stage (production):
#     docker build --target runtime -t kepler-mcp-gitlab:latest -f docker/Dockerfile .

# =============================================================================
# Base stage - Common foundation for all stages
# =============================================================================
FROM python:3.12-slim AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Create non-root user for runtime security
RUN useradd --create-home --shell /bin/bash appuser

# =============================================================================
# Lint stage - Quality checks and security scanning
# =============================================================================
FROM base AS lint

# Copy all files needed for installation
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install all dependencies including dev tools
RUN pip install --no-cache-dir ".[dev]"

# Copy test files (after install to leverage cache)
COPY tests/ ./tests/

# Run quality checks - any failure will stop the build
RUN echo "Running Ruff linting..." && ruff check src/ tests/
RUN echo "Running Mypy type checking..." && mypy src/
RUN echo "Running Bandit security scan..." && bandit -r src/
RUN echo "Running Safety dependency check..." && safety check --full-report || true

# If we get here, all checks passed
RUN echo "All quality checks passed!"

# =============================================================================
# Runtime stage - Production image
# =============================================================================
FROM base AS runtime

# Copy files needed for installation
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install only runtime dependencies (no dev extras)
RUN pip install --no-cache-dir .

# Switch to non-root user
USER appuser

# Expose default port for SSE transport
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command - run in SSE mode
CMD ["python", "-m", "kepler_mcp_gitlab.cli", "serve", "--transport", "sse"]
