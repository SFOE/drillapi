# drillapi
New backend for ich-tanke-strom

## Startup

Create python virtual environment

```python3 -m venv venv```

Activate python virtual environment

```source venv/bin/activate```

Install dependencies

```pip install -r requirements.txt``


Run dev server locally

```fastapi dev src/main.py```

Check everything is fine a

Main route v1

```http://127.0.0.1:8000/v1/2602531.09/1202835.00```


Canton's configuration v2

```http://127.0.0.1:8000/v1/cantons```

OpenAPI doc

```http://127.0.0.1:8000/docs```



