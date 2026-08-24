import pytest
from fastapi.testclient import TestClient

from drillapi.app import app
from drillapi.config import Settings, settings


@pytest.fixture(autouse=True, scope="session")
def override_global_settings():
    test_settings = Settings(
        RATE_LIMIT="100/min",
        ALLOWED_ORIGINS=["*"],
        ENVIRONMENT="TEST",
    )

    for key, value in test_settings.model_dump().items():
        setattr(settings, key, value)

    yield


@pytest.fixture(scope="session")
def client():
    return TestClient(app)
