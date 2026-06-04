"""Tests for the drill category endpoint with real geoservice response data.

Coordinates used:
- JU (Jura, WMS): 2574738, 1249285 — matches JU ground_control_point[0] (expected: 1, "Autorisé")
- FR (Fribourg, ESRI): 2582124, 1164966 — matches FR ground_control_point[0]
"""

import respx
import httpx


@respx.mock
def test_drill_category_wms_gml(client):
    """WMS GML response from Jura is parsed and returns harmonized_value=1."""
    coord_x = 2574738
    coord_y = 1249285

    with open("tests/data/geoadmin/canton_identify_ju.json", "rb") as f:
        canton_json = f.read()

    respx.get("https://api3.geo.admin.ch/rest/services/ech/MapServer/identify").mock(
        return_value=httpx.Response(
            200,
            content=canton_json,
            headers={"Content-Type": "application/json"},
        )
    )

    with open("tests/data/wms/getfeatureinfo_ju.gml", "rb") as f:
        gml = f.read()

    respx.get("https://geoservices.jura.ch/wms").mock(
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
    assert payload["canton"] == "JU"
    assert payload["ground_category"]["harmonized_value"] == 1
    assert "full_url" in payload["result_detail"]
    assert payload["result_detail"]["detail"] is None


@respx.mock
def test_drill_category_esri_json(client):
    """ESRI REST JSON response from Fribourg is parsed and returns harmonized_value=1."""
    coord_x = 2582124
    coord_y = 1164966

    with open("tests/data/geoadmin/canton_identify_fr.json", "rb") as f:
        canton_json = f.read()

    respx.get("https://api3.geo.admin.ch/rest/services/ech/MapServer/identify").mock(
        return_value=httpx.Response(
            200,
            content=canton_json,
            headers={"Content-Type": "application/json"},
        )
    )

    with open("tests/data/esri/identify_fr.json", "rb") as f:
        esri_json = f.read()

    respx.get(
        "https://map.geo.fr.ch/arcgis/rest/services/PortailCarto/Theme_environnement/MapServer/17/query"
    ).mock(
        return_value=httpx.Response(
            200,
            content=esri_json,
            headers={"Content-Type": "application/json"},
        )
    )

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["coord_x"] == coord_x
    assert payload["coord_y"] == coord_y
    assert payload["canton"] == "FR"
    assert payload["ground_category"]["harmonized_value"] == 1
    assert "full_url" in payload["result_detail"]
    assert payload["result_detail"]["detail"] is None
