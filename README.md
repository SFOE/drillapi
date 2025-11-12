# drillapi
[![CI](https://github.com/SFOE/drillapi/actions/workflows/ci.yml/badge.svg)](https://github.com/SFOE/drillapi/actions/workflows/ci.yml)

New backend for kann ich bohren

## Startup

Create .env file and :warning: adapt values :warning

```cp env.example .env```


Create python virtual environment

```python3 -m venv venv```

Activate python virtual environment

```source venv/bin/activate```

Install dependencies

```bash
pip install -r requirements.txt
```

Install pre-commit and activate it

```bash
pip install pre-commit
pre-commit install
```

Run pre-commit manually
```bash
pre-commit run --all-files
```

Run dev server locally with uvicorn

```python -m src.main```

Check everything is fine

Main route v1

```http://127.0.0.1:8000/v1/2602531.09/1202835.00```


Canton's configuration v1

```http://127.0.0.1:8000/v1/cantons```

OpenAPI doc

```http://127.0.0.1:8000/docs```

Run tests

```python -m pytest -v```

Run only service avaibility checker test

```python -m pytest tests/test_services.py```


## Using Docker Compose

```docker compose up -d --build && docker compose logs -f fastapi-app```


## Using Docker

Build local image

```docker build -t fastapi-app .```

Run container


```docker run -d -p 8000:8000 --name fastapi_container fastapi-app```
