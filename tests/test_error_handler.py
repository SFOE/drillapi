"""Tests for the error_handler decorator.

Covers:
- HTTPExceptions pass through unchanged
- Non-HTTP exceptions in PROD mode return 500 with message
- Non-HTTP exceptions in DEV mode re-raise the exception
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from drillapi.services.error_handler import handle_errors
from drillapi.config import settings


@pytest.fixture
def error_app():
    """Create a minimal FastAPI app with decorated endpoints for testing."""
    app = FastAPI()

    @app.get("/http-error")
    @handle_errors
    async def http_error_endpoint():
        raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/generic-error")
    @handle_errors
    async def generic_error_endpoint():
        raise ValueError("Something went wrong")

    @app.get("/success")
    @handle_errors
    async def success_endpoint():
        return {"status": "ok"}

    return app


def test_http_exception_passes_through(error_app):
    """HTTPExceptions raised inside the decorated function are re-raised as-is."""
    client = TestClient(error_app)
    response = client.get("/http-error")
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_generic_exception_returns_500_in_prod(error_app, monkeypatch):
    """Non-HTTP exceptions in PROD return 500 with the exception message."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "PROD")

    client = TestClient(error_app)
    response = client.get("/generic-error")
    assert response.status_code == 500
    assert "Something went wrong" in response.json()["detail"]


def test_generic_exception_reraises_in_dev(error_app, monkeypatch):
    """Non-HTTP exceptions in DEV mode are re-raised (full traceback)."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "DEV")

    client = TestClient(error_app, raise_server_exceptions=False)
    response = client.get("/generic-error")
    # In DEV mode the exception is re-raised, resulting in a 500 from the server
    assert response.status_code == 500


def test_success_passes_through(error_app):
    """Successful endpoints work normally when decorated."""
    client = TestClient(error_app)
    response = client.get("/success")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
