[![CI](https://github.com/SFOE/drillapi/actions/workflows/ci.yml/badge.svg)](https://github.com/SFOE/drillapi/actions/workflows/ci.yml)

# drillapi - geothermal drilling

⚠️this project is under construction ⚠️

***Query the cantonal geoservices to know whether a site in Switzerland is suitable for a geothermal drilling.***

What does this [FastAPI](https://fastapi.tiangolo.com/) project do ?

- take x/y coordinates in EPSG:2056 on route ```/v1/x/y```
- find in which canton the coordinates are and retrieve specific geoservice configuration
- send request to corresponding cantonal geoservices, depending on location
- process and reclass the results
- return reponse used by [drill-frontend](https://github.com/sfOE/drill-frontend) vuejs web app

## Run

This project runs in docker:
- Latest image: ```docker run --rm ghcr.io/sfoe/drillapi:latest```
- Latest image: ```docker run --rm ghcr.io/sfoe/drillapi:<vx.y.z>```

 Default port is ***8000***

## Local setup for development

Create .env file and :warning: adapt values :warning:

Special attention to the ```ENVIRONMENT``` value, MUST never be set to ```DEV``` in production environnement

```bash
cp env.example .env
```

Create python virtual environment

```bash
python3 -m venv venv
```

Activate python virtual environment
```bash
source venv/bin/activate
```

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

## Start

Run dev server locally with fast api dev server

```bash
fastapi dev src/main.py
```

Run dev server locally with uvicorn

```bash
python -m src.main
```

## Explore

OpenAPI doc

```bash
http://127.0.0.1:8000/docs
```

Checker that sends predefined calls to all configured cantons - IP restricted ⚠️

```bash
http://127.0.0.1:8000/checker
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

Run tests

```bash
python -m pytest -v
```

Run only service avaibility checker test

```bash
python -m pytest tests/test_services.py
```

## Running local docker image

### Using Docker Compose

```bash
docker compose up -d --build && docker compose logs -f fastapi-app
```

### Using Docker

Build local image

```bash
docker build -t fastapi-app .
```

Run container


```bash
docker run -d -p 8000:8000 --name fastapi_container fastapi-app
```
