"""Tests for the /checker route.

Covers:
- /checker/ for all cantons
- /checker/{canton} for a single valid canton
- /checker/{canton} for a nonexistent canton
- Checker when get_drill_category raises an exception
"""

import pytest
import respx
import httpx
from fastapi.testclient import TestClient
from drillapi.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _mock_canton_identify(canton_code: str):
    """Mock the geo.admin.ch canton identification endpoint."""
    canton_response = {
        "results": [
            {
                "featureId": 1,
                "layerBodId": "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
                "layerName": "Cantonal boundaries",
                "id": 1,
                "attributes": {"ak": canton_code},
            }
        ]
    }
    respx.get(
        "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify", params=None
    ).mock(
        return_value=httpx.Response(
            200,
            json=canton_response,
            headers={"Content-Type": "application/json"},
        )
    )


@respx.mock
def test_checker_single_valid_canton(client):
    """Test /checker/JU returns HTML with results for a single canton."""
    _mock_canton_identify("JU")

    with open("tests/data/wms/getfeatureinfo_ju.gml", "rb") as f:
        gml = f.read()

    respx.get("https://geoservices.jura.ch/wms", params=None).mock(
        return_value=httpx.Response(
            200,
            content=gml,
            headers={"Content-Type": "application/vnd.ogc.gml"},
        )
    )

    response = client.get("/checker/JU")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # The response contains the canton name
    assert "JU" in response.text


def test_checker_nonexistent_canton(client):
    """Test /checker/XX returns HTML with error message for unknown canton."""
    response = client.get("/checker/XX")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "not found" in response.text.lower()


@respx.mock
def test_checker_geoservice_failure(client):
    """Test /checker/{canton} gracefully handles geoservice errors."""
    _mock_canton_identify("JU")

    # Simulate geoservice timeout
    respx.get("https://geoservices.jura.ch/wms", params=None).mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )

    response = client.get("/checker/JU")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@respx.mock
def test_checker_all_cantons_page_loads(client):
    """Test /checker/ returns HTML (smoke test for all-cantons mode)."""
    # Mock the geo.admin endpoint to return JU for all coordinate lookups
    _mock_canton_identify("JU")

    with open("tests/data/wms/getfeatureinfo_ju.gml", "rb") as f:
        gml = f.read()

    # Mock all WMS/ESRI endpoints broadly
    respx.route().mock(
        return_value=httpx.Response(
            200,
            content=gml,
            headers={"Content-Type": "application/vnd.ogc.gml"},
        )
    )

    response = client.get("/checker/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
