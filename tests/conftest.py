import pytest
from drillapi.config import Settings, settings as global_settings


@pytest.fixture(autouse=True, scope="session")
def override_global_settings():
    """
    Automatically override settings for all tests.
    This fixture is applied to all tests without needing to include it explicitly.
    """
    global global_settings
    global_settings = Settings(
        RATE_LIMIT="100/min",
        ALLOWED_IPS=["127.0.0.1"],
        ALLOWED_ORIGINS=["*"],
        ENVIRONMENT="TEST",
    )
