.PHONY: help install install-dev lint typecheck secscan test coverage check-all serve-stdio serve-sse clean docker-lint docker-runtime

# Default target
help:
	@echo "Kepler MCP Server Template - Available Commands"
	@echo ""
	@echo "Installation:"
	@echo "  install       Install runtime dependencies"
	@echo "  install-dev   Install runtime and development dependencies"
	@echo ""
	@echo "Quality Checks:"
	@echo "  lint          Run Ruff linting"
	@echo "  lint-fix      Run Ruff linting with auto-fix"
	@echo "  typecheck     Run Mypy type checking"
	@echo "  secscan       Run Bandit and Safety security scans"
	@echo "  test          Run pytest"
	@echo "  coverage      Run pytest with coverage reporting"
	@echo "  check-all     Run all quality checks in sequence"
	@echo ""
	@echo "Server:"
	@echo "  serve-stdio   Run server in stdio mode"
	@echo "  serve-sse     Run server in SSE mode"
	@echo ""
	@echo "Docker:"
	@echo "  docker-lint     Build lint stage Docker image"
	@echo "  docker-runtime  Build runtime stage Docker image"
	@echo "  docker-all      Build both lint and runtime images"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean         Remove build artifacts and caches"

# Installation
install:
	pip install .

install-dev:
	pip install -e ".[dev]"

# Linting
lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

# Type checking
typecheck:
	mypy src/

# Security scanning
secscan:
	@echo "Running Bandit security scan..."
	bandit -r src/
	@echo ""
	@echo "Running Safety dependency check..."
	safety check --full-report

# Testing
test:
	pytest tests/

coverage:
	pytest --cov=src/kepler_mcp_gitlab --cov-report=html --cov-report=term tests/
	@echo "Coverage report generated in htmlcov/"

# Run all checks
check-all: lint typecheck secscan test
	@echo ""
	@echo "All checks passed!"

# Server commands
serve-stdio:
	python -m kepler_mcp_gitlab.cli serve --transport stdio

serve-sse:
	python -m kepler_mcp_gitlab.cli serve --transport sse

# Docker
docker-lint:
	docker build --target lint -t kepler-mcp-gitlab:lint -f docker/Dockerfile .

docker-runtime:
	docker build --target runtime -t kepler-mcp-gitlab:latest -f docker/Dockerfile .

docker-all: docker-lint docker-runtime
	@echo "Docker images built: kepler-mcp-gitlab:lint, kepler-mcp-gitlab:latest"

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
