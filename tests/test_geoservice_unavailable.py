"""Tests for geoservice unavailability handling.

Verifies that when external cantonal geoservices fail (timeout, connection error,
invalid response), the backend returns a structured HTTP 200 response with
harmonized_value=98 and the canton identifier, instead of raising HTTPException(502).
Canton config is preserved so the frontend can access cantonal_energy_service_url.
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
def test_wms_timeout_returns_structured_response(client):
    """When a WMS geoservice times out, return HTTP 200 with harmonized_value=98."""
    coord_x = 2574738
    coord_y = 1249285

    _mock_canton_identify("JU")

    respx.get("https://geoservices.jura.ch/wms", params=None).mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canton"] == "JU"
    assert payload["ground_category"]["harmonized_value"] == 98
    assert payload["ground_category"]["source_values"] == "geoservice unavailable"
    assert payload["result_detail"]["message"] == "External geoservice unavailable"
    assert payload["canton_config"] is not None
    assert payload["canton_config"]["name"] == "JU"


@respx.mock
def test_esri_connection_error_returns_structured_response(client):
    """When an ESRI REST geoservice has a connection error, return HTTP 200 with harmonized_value=98."""
    coord_x = 2582124
    coord_y = 1164966

    _mock_canton_identify("FR")

    respx.get(
        "https://map.geo.fr.ch/arcgis/rest/services/PortailCarto/Theme_environnement/MapServer/17/query",
        params=None,
    ).mock(side_effect=httpx.ConnectError("Connection refused"))

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canton"] == "FR"
    assert payload["ground_category"]["harmonized_value"] == 98
    assert payload["ground_category"]["source_values"] == "geoservice unavailable"
    assert payload["result_detail"]["message"] == "External geoservice unavailable"
    assert payload["canton_config"] is not None
    assert payload["canton_config"]["name"] == "FR"


@respx.mock
def test_wms_http_500_returns_structured_response(client):
    """When a WMS geoservice returns HTTP 500, return HTTP 200 with harmonized_value=98."""
    coord_x = 2574738
    coord_y = 1249285

    _mock_canton_identify("JU")

    respx.get("https://geoservices.jura.ch/wms", params=None).mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canton"] == "JU"
    assert payload["ground_category"]["harmonized_value"] == 98
    assert payload["ground_category"]["source_values"] == "geoservice unavailable"
    assert payload["canton_config"] is not None
    assert payload["canton_config"]["name"] == "JU"


@respx.mock
def test_successful_wms_still_works(client):
    """Successful WMS responses should still return normal suitability values (preservation)."""
    coord_x = 2574738
    coord_y = 1249285

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

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ground_category"]["harmonized_value"] == 1
    assert payload["result_detail"]["message"] == "Success"


@respx.mock
def test_canton_preserved_in_geoservice_failure(client):
    """Canton identifier and config must be preserved in the response when geoservice fails."""
    coord_x = 2574738
    coord_y = 1249285

    _mock_canton_identify("JU")

    respx.get("https://geoservices.jura.ch/wms", params=None).mock(
        side_effect=httpx.ReadTimeout("Read timed out")
    )

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    # Canton must be preserved
    assert payload["canton"] == "JU"
    # Canton config preserved so frontend can access cantonal_energy_service_url
    assert payload["canton_config"] is not None
    assert payload["canton_config"]["name"] == "JU"
    assert payload["canton_config"]["cantonal_energy_service_url"] is not None
    assert payload["ground_category"]["harmonized_value"] == 98
