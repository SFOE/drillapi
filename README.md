[![CI](https://github.com/SFOE/drillapi/actions/workflows/ci.yml/badge.svg)](https://github.com/SFOE/drillapi/actions/workflows/ci.yml)

# drillapi - geothermal drilling

***Query the cantonal geoservices to know whether a site in Switzerland is suitable for a geothermal drilling.***

This project uses [UV](https://github.com/astral-sh/uv) for dependency management.

What does this [FastAPI](https://fastapi.tiangolo.com/) project do ?

- take x/y coordinates in EPSG:2056 on route ```/v1/x/y```
- find in which canton the coordinates are and retrieve specific geoservice configuration
- send request to corresponding cantonal geoservices, depending on location
- process and reclass the results (1: OK, 2: With restriction, 3: Forbidden, 4: Unknown or Service Error)
- return reponse used by [drill-frontend](https://github.com/sfOE/drill-frontend) vuejs web app

## Run

This project can run in docker:

***Latest image***

 ```bash
docker run -d \
  -p 8000:8000 \
  -e RATE_LIMIT="1000/minute" \
  -e ALLOWED_IPS='["127.0.0.1","192.168.1.10"]' \
  -e ALLOWED_ORIGINS='["http://localhost:5173","https://www.uvek-gis.admin.ch/"]' \
  -e ENVIRONMENT=PROD \
  ghcr.io/sfoe/drillapi:latest
```

***Release specific image***

 ```bash
docker run -d \
  -p 8000:8000 \
  -e RATE_LIMIT="1000/minute" \
  -e ALLOWED_IPS='["127.0.0.1","192.168.1.10"]' \
  -e ALLOWED_ORIGINS='["http://localhost:5173","https://www.uvek-gis.admin.ch/"]' \
  -e ENVIRONMENT=PROD \
  ghcr.io/sfoe/drillapi:<vx.y.z>
```

## Local setup for development

Create .env file and :warning: adapt values :warning:

Special attention to the ```ENVIRONMENT``` value, MUST never be set to ```DEV``` in production environnement

```bash
cp env.example .env
```

Install dependencies using UV

```bash
uv sync
```

For **dev** install dev requirements

```bash
uv sync --extra dev
```

Activate pre-commit

```bash
uv run pre-commit install
```

Run pre-commit manually
```bash
uv run pre-commit run --all-files
```

## Start

Run dev server

```bash
uv run uvicorn drillapi.app:app --reload
```

Run project

```bash
uv run python -m drillapi
```

## Explore

OpenAPI doc

```bash
http://127.0.0.1:8000/docs
```

Checker that sends predefined calls to all configured cantons

```bash
http://127.0.0.1:8000/checker
```

Or check one canton only

```bash
http://127.0.0.1:8000/checker/VD
```

Main route v1

```bash
http://127.0.0.1:8000/v1/drill-category/2602531.09/1202835.00
```

Canton's configuration v1

```bash
http://127.0.0.1:8000/v1/cantons
```

Canton's configuration v1 for one canton's code ("NE", "BE")

```bash
http://127.0.0.1:8000/v1/cantons/NE
```

## Test

Install dev requirements

```bash
uv sync --extra dev
```

Run tests

```bash
uv run python -m pytest -v
```

## Running local docker image

### Using Docker Compose

```bash
docker compose up -d --build && docker compose logs -f drillapi
```

### Using Docker

Build local image

```bash
docker build -t drillapi .
```

Run container

```bash
docker run -d -p 8000:8000 --name drillapi_container drillapi
```

View logs

```bash
docker logs -f drillapi_container
```

Stop container

```bash
docker stop drillapi_container
docker rm drillapi_container
```
