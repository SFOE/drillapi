"""Tests for drillapi.services.processing module.

Covers:
- normalize_string with non-string input
- get_canton_from_coordinates error handling (network, HTTP, JSON errors)
- parse_wms_getfeatureinfo with GeoJSON FeatureCollection
- parse_wms_getfeatureinfo with ESRI REST JSON
- parse_wms_getfeatureinfo with invalid XML/GML
- parse_wms_getfeatureinfo ZH special case
- process_ground_category with no matching features (fallback harmonized_value=4)
- process_ground_category with layer-name-based matching (no property_values)
"""

import json
import pytest
import respx
import httpx
from drillapi.services.processing import (
    normalize_string,
    get_canton_from_coordinates,
    parse_wms_getfeatureinfo,
    process_ground_category,
)


# --- normalize_string ---


def test_normalize_string_non_string_input():
    """Non-string input should be returned unchanged."""
    assert normalize_string(123) == 123
    assert normalize_string(None) is None
    assert normalize_string([]) == []


def test_normalize_string_normal_string():
    """Normal ASCII strings pass through unchanged."""
    assert normalize_string("hello") == "hello"


# --- get_canton_from_coordinates error handling ---


@pytest.mark.asyncio
@respx.mock
async def test_get_canton_network_error():
    """Network errors return empty results instead of raising."""
    respx.get(
        "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify", params=None
    ).mock(side_effect=httpx.ConnectError("Connection refused"))

    result = await get_canton_from_coordinates(2600000, 1200000)
    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_get_canton_http_500():
    """HTTP 500 from geo.admin.ch returns empty results."""
    respx.get(
        "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify", params=None
    ).mock(return_value=httpx.Response(500, text="Internal Server Error"))

    result = await get_canton_from_coordinates(2600000, 1200000)
    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_get_canton_invalid_json():
    """Invalid JSON response returns empty results."""
    respx.get(
        "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify", params=None
    ).mock(
        return_value=httpx.Response(
            200, content=b"not json", headers={"Content-Type": "application/json"}
        )
    )

    result = await get_canton_from_coordinates(2600000, 1200000)
    assert result == []


# --- parse_wms_getfeatureinfo ---


def test_parse_geojson_featurecollection():
    """GeoJSON FeatureCollection is parsed correctly."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "layerName": "test_layer",
                "properties": {"category": "OK", "depth": 100},
            },
            {
                "type": "Feature",
                "layerName": "test_layer_2",
                "properties": {"category": "Restricted"},
            },
        ],
    }
    content = json.dumps(geojson).encode("utf-8")
    config = {"name": "TEST"}

    features = parse_wms_getfeatureinfo(content, "application/json", config)

    assert len(features) == 2
    assert features[0]["category"] == "OK"
    assert features[0]["depth"] == 100
    assert features[0]["layerName"] == "test_layer"
    assert features[1]["category"] == "Restricted"


def test_parse_esri_rest_json():
    """ESRI REST JSON response is parsed correctly."""
    esri_data = {
        "features": [
            {
                "attributes": {"OBJECTID": 1, "zone": "allowed"},
                "layerName": "geothermie",
            }
        ]
    }
    content = json.dumps(esri_data).encode("utf-8")
    config = {"name": "FR"}

    features = parse_wms_getfeatureinfo(content, "arcgis/json", config)

    assert len(features) == 1
    assert features[0]["OBJECTID"] == 1
    assert features[0]["zone"] == "allowed"
    assert features[0]["layerName"] == "geothermie"


def test_parse_invalid_xml_raises_http_exception():
    """Invalid XML/GML content raises HTTPException(500)."""
    from fastapi import HTTPException

    content = b"this is not xml at all <><><>"
    config = {"name": "TEST"}

    with pytest.raises(HTTPException) as exc_info:
        parse_wms_getfeatureinfo(content, "application/vnd.ogc.gml", config)

    assert exc_info.value.status_code == 500


def test_parse_zh_special_case():
    """ZH canton special GML parsing extracts gml:name element."""
    gml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
    <wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs"
                           xmlns:gml="http://www.opengis.net/gml">
        <gml:name>Auflagen</gml:name>
    </wfs:FeatureCollection>
    """
    config = {"name": "ZH"}

    features = parse_wms_getfeatureinfo(gml_content, "application/vnd.ogc.gml", config)

    assert len(features) == 1
    assert features[0]["name"] == "Auflagen"


def test_parse_zh_no_name_element():
    """ZH canton returns empty if no gml:name element."""
    gml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
    <wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs"
                           xmlns:gml="http://www.opengis.net/gml">
    </wfs:FeatureCollection>
    """
    config = {"name": "ZH"}

    features = parse_wms_getfeatureinfo(gml_content, "application/vnd.ogc.gml", config)

    assert features == []


# --- process_ground_category ---


def test_process_ground_category_no_matching_features():
    """When no features match, fallback harmonized_value should be 4 (UNKNOWN)."""
    ground_features = [{"some_field": "some_value"}]
    config_layers = [
        {
            "name": "test_layer",
            "property_name": "category",
            "property_values": [
                {"name": "OK", "desc": "OK", "target_harmonized_value": 1},
            ],
        }
    ]

    result = process_ground_category(ground_features, config_layers)

    assert result.harmonized_value == 4
    assert result.source_values == ""


def test_process_ground_category_empty_features():
    """Empty features list should return harmonized_value=4."""
    result = process_ground_category(
        [], [{"name": "l", "property_name": "p", "property_values": []}]
    )
    assert result.harmonized_value == 4


def test_process_ground_category_layer_name_matching():
    """When no property_values, matching is done by layerName."""
    ground_features = [{"layerName": "restriction_layer"}]
    config_layers = [
        {
            "name": "restriction_layer",
            "property_name": "restriction_layer",
            "property_values": None,
            "target_harmonized_value": 3,
        }
    ]

    result = process_ground_category(ground_features, config_layers)

    assert result.harmonized_value == 3


def test_process_ground_category_max_value_wins():
    """When multiple layers match, the highest harmonized value wins."""
    ground_features = [
        {"category": "OK"},
        {"category": "Forbidden"},
    ]
    config_layers = [
        {
            "name": "test_layer",
            "property_name": "category",
            "property_values": [
                {"name": "OK", "desc": "OK", "target_harmonized_value": 1},
                {
                    "name": "Forbidden",
                    "desc": "Forbidden",
                    "target_harmonized_value": 3,
                },
            ],
        }
    ]

    result = process_ground_category(ground_features, config_layers)

    assert result.harmonized_value == 3
    assert "Forbidden" in result.source_values
