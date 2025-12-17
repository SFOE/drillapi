FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/drillapi ./drillapi
COPY tests ./tests

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "drillapi.app:app", "--host", "0.0.0.0", "--port", "8000"]