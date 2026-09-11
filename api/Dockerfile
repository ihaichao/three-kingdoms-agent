FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY uv.lock pyproject.toml README.md ./
RUN uv sync --frozen --no-cache

COPY src/three_kingdoms three_kingdoms/
COPY tools tools/

CMD ["/app/.venv/bin/fastapi", "run", "three_kingdoms/infrastructure/api.py", "--port", "8000", "--host", "0.0.0.0"]
