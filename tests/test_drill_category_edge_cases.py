"""Tests for drill_category route edge cases.

Covers:
- Coordinates outside Switzerland (no canton found) → harmonized_value=6
- Coordinates in an inactive canton → harmonized_value=5
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


@respx.mock
def test_coordinates_outside_switzerland(client):
    """When geo.admin.ch returns no canton, response has harmonized_value=6."""
    coord_x = 2600000
    coord_y = 1200000

    # geo.admin returns empty results (coordinates not in Switzerland)
    respx.get(
        "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify", params=None
    ).mock(
        return_value=httpx.Response(
            200,
            json={"results": []},
            headers={"Content-Type": "application/json"},
        )
    )

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ground_category"]["harmonized_value"] == 6
    assert "No canton found" in payload["result_detail"]["message"]


@respx.mock
def test_coordinates_in_inactive_canton(client):
    """When canton is inactive, response has harmonized_value=5."""
    coord_x = 2600000
    coord_y = 1200000

    # geo.admin returns NE which is inactive
    canton_response = {
        "results": [
            {
                "featureId": 1,
                "layerBodId": "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
                "layerName": "Cantonal boundaries",
                "id": 1,
                "attributes": {"ak": "NE"},
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

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canton"] == "NE"
    assert payload["ground_category"]["harmonized_value"] == 5
    assert "not active" in payload["result_detail"]["message"].lower()


@respx.mock
def test_coordinates_in_canton_without_config(client):
    """When canton has no configuration at all, response has harmonized_value=5."""
    coord_x = 2600000
    coord_y = 1200000

    # geo.admin returns a canton that doesn't exist in config
    canton_response = {
        "results": [
            {
                "featureId": 1,
                "layerBodId": "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
                "layerName": "Cantonal boundaries",
                "id": 1,
                "attributes": {"ak": "XX"},
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

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ground_category"]["harmonized_value"] == 5
