FROM ghcr.io/astral-sh/uv:python3.14-alpine

WORKDIR /app
ENV PYTHONPATH=/app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/drillapi ./drillapi

RUN uv sync --no-install-project

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "drillapi.app:app", "--host", "0.0.0.0", "--port", "8000"]