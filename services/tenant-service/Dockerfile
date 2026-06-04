# services/tenant-service/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared package first (cached layer)
COPY packages/erp-shared /packages/erp-shared

# Install dependencies
COPY services/tenant-service/pyproject.toml .
RUN uv sync --no-dev 2>/dev/null || uv sync --no-dev --no-frozen

# Copy application code
COPY services/tenant-service/app ./app
COPY services/tenant-service/alembic ./alembic
COPY services/tenant-service/alembic.ini .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
