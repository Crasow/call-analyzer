FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

RUN uv sync --frozen --no-dev

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && mkdir -p /app/uploads /app/watch \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["uv", "run", "ca", "serve", "--host", "0.0.0.0", "--port", "8080"]
