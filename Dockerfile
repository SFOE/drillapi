FROM python:3.14-slim

WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/drillapi ./drillapi
COPY tests ./tests

RUN uv sync --no-install-project

EXPOSE 8000

CMD ["uvicorn", "drillapi.app:app", "--host", "0.0.0.0", "--port", "8000"]