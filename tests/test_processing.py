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

import httpx
import pytest
import respx

from drillapi.services.processing import (
    _wfs_response_has_feature,
    fetch_features_for_point,
    get_canton_from_coordinates,
    normalize_string,
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


# --- WFS presence-based support (ZH) ---

_WFS_WITH_FEATURE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
    b'xmlns:ms="http://mapserver.gis.umn.edu/mapserver" '
    b'numberMatched="1" numberReturned="1">'
    b'<wfs:member><ms:waermenutzung-zone-b gml:id="waermenutzung-zone-b.1"/>'
    b"</wfs:member></wfs:FeatureCollection>"
)

_WFS_EMPTY = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
    b'numberMatched="unknown" numberReturned="0"></wfs:FeatureCollection>'
)

_WFS_EXCEPTION = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows" version="2.0.0">'
    b'<ows:Exception exceptionCode="InvalidParameterValue"/>'
    b"</ows:ExceptionReport>"
)


def test_wfs_response_has_feature_true():
    """numberReturned > 0 means the layer intersects the point."""
    assert _wfs_response_has_feature(_WFS_WITH_FEATURE) is True


def test_wfs_response_has_feature_false():
    """numberReturned == 0 means no feature at the point."""
    assert _wfs_response_has_feature(_WFS_EMPTY) is False


def test_wfs_response_has_feature_member_fallback():
    """A member element counts as a feature when numberReturned is absent."""
    content = (
        b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0">'
        b"<wfs:member/></wfs:FeatureCollection>"
    )
    assert _wfs_response_has_feature(content) is True


def test_wfs_response_exception_raises():
    """A WFS exception report must raise so the caller flags the geoservice."""
    with pytest.raises(ValueError, match="service exception"):
        _wfs_response_has_feature(_WFS_EXCEPTION)


_ZH_WFS_CONFIG = {
    "name": "ZH",
    "info_format": "application/wfs",
    "bbox_delta": 30,
    "query_url": "https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS",
    "layers": [
        {
            "name": "waermenutzung-zone-a",
            "property_name": "waermenutzung-zone-a",
            "target_harmonized_value": 3,
            "desc": "Zone A",
        },
        {
            "name": "waermenutzung-zone-b",
            "property_name": "waermenutzung-zone-b",
            "target_harmonized_value": 2,
            "desc": "Zone B",
        },
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_wfs_presence_tags_matching_layer():
    """A WFS layer that returns a feature is tagged with its layerName."""
    route = respx.get("https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS")

    def _responder(request):
        if "waermenutzung-zone-b" in str(request.url):
            return httpx.Response(200, content=_WFS_WITH_FEATURE)
        return httpx.Response(200, content=_WFS_EMPTY)

    route.mock(side_effect=_responder)

    result = await fetch_features_for_point(2681563, 1248410, _ZH_WFS_CONFIG)

    assert result.get("geoservice_unavailable") is None
    assert result["features"] == [{"layerName": "waermenutzung-zone-b"}]

    gc = process_ground_category(result["features"], _ZH_WFS_CONFIG["layers"])
    assert gc.harmonized_value == 2
    assert gc.source_values == "Zone B"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_wfs_exception_is_geoservice_unavailable():
    """A WFS exception report surfaces as geoservice_unavailable, not 'no match'."""
    respx.get("https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS").mock(
        return_value=httpx.Response(200, content=_WFS_EXCEPTION)
    )

    result = await fetch_features_for_point(2681563, 1248410, _ZH_WFS_CONFIG)

    assert result["geoservice_unavailable"] is True
    assert result["features"] == []


@pytest.mark.asyncio
@respx.mock
async def test_fetch_wfs_http_error_is_geoservice_unavailable():
    """A network/HTTP failure on a WFS layer flags the geoservice as unavailable."""
    respx.get("https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS").mock(
        side_effect=httpx.ConnectError("boom")
    )

    result = await fetch_features_for_point(2681563, 1248410, _ZH_WFS_CONFIG)

    assert result["geoservice_unavailable"] is True
