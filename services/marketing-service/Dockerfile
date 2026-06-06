FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/erp-shared /packages/erp-shared
COPY services/marketing-service/pyproject.toml .
RUN uv sync --no-dev 2>/dev/null || uv sync --no-dev --no-frozen

COPY services/marketing-service/app ./app
COPY services/marketing-service/alembic ./alembic
COPY services/marketing-service/alembic.ini .

EXPOSE 8005
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
