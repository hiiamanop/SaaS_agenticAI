# services/inventory-service/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/erp-shared /packages/erp-shared

COPY services/inventory-service/pyproject.toml .
RUN uv sync --no-dev 2>/dev/null || uv sync --no-dev --no-frozen

COPY services/inventory-service/app ./app
COPY services/inventory-service/alembic ./alembic
COPY services/inventory-service/alembic.ini .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
