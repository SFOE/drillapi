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
def test_drill_category_wms_gml(client):
    coord_x = 2574738
    coord_y = 1249285

    with open("tests/data/geoadmin/canton_identify_ju.json", "rb") as f:
        canton_json = f.read()

    respx.get(
        "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify", params=None
    ).mock(
        return_value=httpx.Response(
            200,
            content=canton_json,
            headers={"Content-Type": "application/json"},
        )
    )

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
    assert payload["coord_x"] == coord_x
    assert payload["coord_y"] == coord_y
    assert payload["ground_category"]
    assert payload["ground_category"]["harmonized_value"] == 1
    assert "full_url" in payload["result_detail"]
    assert payload["result_detail"]["detail"] is None


@respx.mock
def test_drill_category_esri_json(client):
    coord_x = 2582124
    coord_y = 1164966

    with open("tests/data/geoadmin/canton_identify_fr.json", "rb") as f:
        canton_json = f.read()

    respx.get(
        "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify", params=None
    ).mock(
        return_value=httpx.Response(
            200,
            content=canton_json,
            headers={"Content-Type": "application/json"},
        )
    )

    with open("tests/data/esri/identify_fr.json", "rb") as f:
        json = f.read()

    respx.get(
        "https://map.geo.fr.ch/arcgis/rest/services/PortailCarto/Theme_environnement/MapServer/17/query",
        params=None,
    ).mock(
        return_value=httpx.Response(
            200,
            content=json,
            headers={"Content-Type": "application/json"},
        )
    )

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["coord_x"] == coord_x
    assert payload["coord_y"] == coord_y
    assert payload["ground_category"]
    assert payload["ground_category"]["harmonized_value"] == 1
    assert "full_url" in payload["result_detail"]
    assert payload["result_detail"]["detail"] is None
