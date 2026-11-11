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
    _parse_wfs_features,
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


# --- WFS support (presence- and attribute-based) ---

# A presence-only feature (geometry only, no attributes) — ZH zone layers.
_WFS_PRESENCE_ONLY = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
    b'xmlns:gml="http://www.opengis.net/gml/3.2" '
    b'xmlns:ms="http://mapserver.gis.umn.edu/mapserver" '
    b'numberMatched="1" numberReturned="1">'
    b'<wfs:member><ms:waermenutzung-zone-b gml:id="waermenutzung-zone-b.1">'
    b'<ms:msGeometry><gml:Polygon gml:id="p.1"/></ms:msGeometry>'
    b"</ms:waermenutzung-zone-b></wfs:member></wfs:FeatureCollection>"
)

# An attribute-carrying feature (BL ohne_a style: ov_kategor + geometry).
_WFS_WITH_ATTR = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
    b'xmlns:gml="http://www.opengis.net/gml/3.2" '
    b'xmlns:ms="http://mapserver.gis.umn.edu/mapserver" '
    b'numberMatched="1" numberReturned="1">'
    b'<wfs:member><ms:erdwaerme_uebersicht_ohne_a gml:id="f.1">'
    b'<ms:geom><gml:Polygon gml:id="p.1"/></ms:geom>'
    b"<ms:ov_kategor>C</ms:ov_kategor>"
    b"<ms:ov_kategor_txt>Fall C</ms:ov_kategor_txt>"
    b"</ms:erdwaerme_uebersicht_ohne_a></wfs:member></wfs:FeatureCollection>"
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
    assert _wfs_response_has_feature(_WFS_PRESENCE_ONLY) is True


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


def test_parse_wfs_features_presence_only():
    """A geometry-only feature parses to an (attribute-less) dict."""
    feats = _parse_wfs_features(_WFS_PRESENCE_ONLY)
    assert len(feats) == 1
    # Geometry is skipped, so no attribute keys remain.
    assert feats[0] == {}


def test_parse_wfs_features_with_attributes():
    """Attribute tags are parsed (namespace-stripped); geometry is skipped."""
    feats = _parse_wfs_features(_WFS_WITH_ATTR)
    assert len(feats) == 1
    assert feats[0]["ov_kategor"] == "C"
    assert feats[0]["ov_kategor_txt"] == "Fall C"
    assert "geom" not in feats[0]


def test_parse_wfs_features_exception_raises():
    """An exception report raises instead of returning an empty list."""
    with pytest.raises(ValueError, match="service exception"):
        _parse_wfs_features(_WFS_EXCEPTION)


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
    """A presence-only WFS layer that returns a feature is tagged with layerName."""
    route = respx.get("https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS")

    def _responder(request):
        if "waermenutzung-zone-b" in str(request.url):
            return httpx.Response(200, content=_WFS_PRESENCE_ONLY)
        return httpx.Response(200, content=_WFS_EMPTY)

    route.mock(side_effect=_responder)

    result = await fetch_features_for_point(2681563, 1248410, _ZH_WFS_CONFIG)

    assert result.get("geoservice_unavailable") is None
    assert result["features"] == [{"layerName": "waermenutzung-zone-b"}]

    gc = process_ground_category(result["features"], _ZH_WFS_CONFIG["layers"])
    assert gc.harmonized_value == 2
    assert gc.source_values == "Zone B"


_BL_WFS_CONFIG = {
    "name": "BL",
    "info_format": "application/wfs",
    "bbox_delta": 10,
    "query_url": "https://geowms.bl.ch/",
    # Fall A is encoded as a hole in ohne_a: no feature -> this default.
    "default_harmonized_value": 3,
    "layers": [
        {
            "name": "erdwaerme_uebersicht_ohne_a",
            "property_name": "ov_kategor",
            "geometry_property": "geom",
            "property_values": [
                {"name": "C", "target_harmonized_value": 1, "desc": "Fall C"},
                {"name": "B", "target_harmonized_value": 2, "desc": "Fall B"},
            ],
        },
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_wfs_uses_intersects_point_filter():
    """The WFS request uses a point INTERSECTS filter, not a bbox."""
    route = respx.get("https://geowms.bl.ch/").mock(
        return_value=httpx.Response(200, content=_WFS_WITH_ATTR)
    )

    await fetch_features_for_point(2620000, 1260000, _BL_WFS_CONFIG)

    sent = str(route.calls.last.request.url)
    assert "FILTER=" in sent
    assert "Intersects" in sent
    assert "BBOX=" not in sent


@pytest.mark.asyncio
@respx.mock
async def test_fetch_wfs_attribute_matching():
    """An attribute-carrying WFS layer maps ov_kategor -> harmonized value."""
    respx.get("https://geowms.bl.ch/").mock(
        return_value=httpx.Response(200, content=_WFS_WITH_ATTR)
    )

    result = await fetch_features_for_point(2622256, 1258565, _BL_WFS_CONFIG)

    assert result.get("geoservice_unavailable") is None
    assert result["features"] == [
        {
            "ov_kategor": "C",
            "ov_kategor_txt": "Fall C",
            "layerName": "erdwaerme_uebersicht_ohne_a",
        }
    ]

    gc = process_ground_category(
        result["features"],
        _BL_WFS_CONFIG["layers"],
        _BL_WFS_CONFIG["default_harmonized_value"],
    )
    assert gc.harmonized_value == 1
    assert gc.source_values == "Fall C"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_wfs_fall_a_hole_uses_default():
    """A Fall A location returns no ohne_a feature, so the canton default (3) wins."""
    respx.get("https://geowms.bl.ch/").mock(
        return_value=httpx.Response(200, content=_WFS_EMPTY)
    )

    result = await fetch_features_for_point(2623369, 1261302, _BL_WFS_CONFIG)

    assert result.get("geoservice_unavailable") is None
    assert result["features"] == []

    gc = process_ground_category(
        result["features"],
        _BL_WFS_CONFIG["layers"],
        _BL_WFS_CONFIG["default_harmonized_value"],
    )
    assert gc.harmonized_value == 3


def test_process_ground_category_default_override():
    """default_harmonized_value replaces the hardcoded 4 fallback when set."""
    result = process_ground_category(
        [{"some": "thing"}],
        [
            {
                "name": "l",
                "property_name": "cat",
                "property_values": [
                    {"name": "X", "target_harmonized_value": 1, "desc": "x"}
                ],
            }
        ],
        default_harmonized_value=3,
    )
    assert result.harmonized_value == 3


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
