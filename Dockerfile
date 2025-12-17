# Use LOCAL_DEV=1 to run uvicorn for local deployment
FROM public.ecr.aws/lambda/python:3.13

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/drillapi ./drillapi
COPY tests ./tests

RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Use LOCAL_DEV=1 to run uvicorn for local deployment
CMD ["sh", "-c", "if [ \"$LOCAL_DEV\" = '1' ]; then uvicorn drillapi.app:app --host 0.0.0.0 --port 8000; else drillapi.app.handler; fi"]
