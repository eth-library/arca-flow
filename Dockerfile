# Stage 1: Build dependencies and install project
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies only (cached unless pyproject.toml or uv.lock change)
RUN uv sync --frozen --extra production --no-dev --no-install-project --no-editable

# Copy application source
COPY arca/ arca/

# Install the project itself
RUN uv sync --frozen --extra production --no-dev --no-editable

# Stage 2: Minimal runtime image
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment with all installed packages
COPY --from=builder /app/.venv /app/.venv

# Add venv to PATH so dagster CLI is available (required by Helm chart)
ENV PATH="/app/.venv/bin:$PATH"

# Ensure Python output is sent straight to the container logs
ENV PYTHONUNBUFFERED=1
