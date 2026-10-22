"""Preservation property tests for the ZH canton drill-category bugfix.

These tests encode the behavior that MUST remain byte-for-byte identical for
every input where the ZH bug condition does NOT hold -- i.e. for every canton
other than ZH, and for transport-level failures (which short-circuit before
any canton-specific parsing happens).

**Observation-first methodology**: each test below was derived by first
observing the CURRENT (unfixed) behavior of `parse_wms_getfeatureinfo`,
`process_ground_category`, and `fetch_features_for_point` directly (manual
probes against the existing JU fixture and hand-built GML/config inputs; see
``.kiro/specs/zh-canton-drill-category-unknown/design.md``), then writing a
property that captures the observed invariant.

**Property 2: Preservation** - for any input where the bug condition does NOT
hold (canton != ZH, or a transport-level failure), the fixed code SHALL
produce exactly the same result as the original code:

- `parse_wms_getfeatureinfo`'s `gml:featureMember` extraction is unchanged.
- `parse_wms_getfeatureinfo`'s MapServer `*_feature` extraction is unchanged.
- `process_ground_category`'s `property_values` / layer-presence matching is
  unchanged for every layer without `bbox_zones`.
- `fetch_features_for_point`'s WMS branch builds `QUERY_LAYERS` identical to
  `LAYERS` for every canton config without a `queryable: false` entry.
- Transport-level failures (timeout, 4xx/5xx, connection error) continue to
  return `geoservice_unavailable`, for both ZH and non-ZH cantons.

None of these code paths are touched by the eventual fix (which is gated on
`config["name"] == "ZH"` / the new, additive `bbox_zones`/`queryable` fields),
so these tests are expected to PASS now (task 2, on unfixed code) AND after
the fix is implemented (task 3.8, same tests re-run unchanged).

**EXPECTED OUTCOME on unfixed code: these tests PASS.**

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

from __future__ import annotations

import asyncio
import string
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from hypothesis import given, settings
from hypothesis import strategies as st

from drillapi.services.processing import (
    fetch_features_for_point,
    parse_wms_getfeatureinfo,
    process_ground_category,
)

# Tags that parse_wms_getfeatureinfo deliberately skips (geometry noise), see
# the `if tag.lower() in (...)` checks in both the featureMember and
# MapServer *_feature branches.
EXCLUDED_TAGS = {"boundedby", "geometry", "polygon", "multipolygon"}

# Restrict generated XML tag/text content to a safe ASCII subset so we don't
# need to reason about XML escaping/encoding edge cases -- those are
# orthogonal to the preservation property under test here.
safe_tag_name = st.text(
    alphabet=string.ascii_lowercase, min_size=3, max_size=10
).filter(lambda s: s not in EXCLUDED_TAGS)
safe_text_value = (
    st.text(
        alphabet=string.ascii_letters + string.digits + " ", min_size=1, max_size=20
    )
    .map(str.strip)
    .filter(lambda s: len(s) > 0)
)
non_zh_canton_code = st.text(
    alphabet=string.ascii_uppercase, min_size=2, max_size=2
).filter(lambda s: s != "ZH")


# --- Observed pattern 1: gml:featureMember extraction (e.g. JU fixture) ---


@given(
    tags_values=st.lists(
        st.tuples(safe_tag_name, safe_text_value),
        min_size=1,
        max_size=5,
        unique_by=lambda tv: tv[0],
    )
)
@settings(max_examples=25)
def test_gml_feature_member_extraction_preserved(tags_values):
    """parse_wms_getfeatureinfo's gml:featureMember extraction returns a
    single feature dict mapping each non-excluded child tag to its stripped
    text, exactly as observed today against the JU fixture
    (tests/data/wms/getfeatureinfo_ju.gml), which this synthesizes the shape
    of for arbitrary tag/value combinations.
    """
    body = "".join(f"<app:{tag}>{value}</app:{tag}>" for tag, value in tags_values)
    gml = f"""<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs"
                       xmlns:gml="http://www.opengis.net/gml"
                       xmlns:app="http://example.com/app">
  <gml:featureMember>
    <app:layer_wrapper>
      {body}
    </app:layer_wrapper>
  </gml:featureMember>
</wfs:FeatureCollection>"""

    features = parse_wms_getfeatureinfo(
        gml.encode("utf-8"), "application/vnd.ogc.gml", {"name": "XX"}
    )

    expected = dict(tags_values)
    assert features == [expected]


# --- Observed pattern 2: MapServer *_feature extraction (msGMLOutput) ---


@given(
    tags_values=st.lists(
        st.tuples(safe_tag_name, safe_text_value),
        min_size=1,
        max_size=5,
        unique_by=lambda tv: tv[0],
    )
)
@settings(max_examples=25)
def test_mapserver_feature_extraction_preserved(tags_values):
    """parse_wms_getfeatureinfo's MapServer `*_feature` extraction returns a
    single feature dict mapping each non-excluded direct child tag to its
    stripped text, exactly as observed today in the JU fixture's
    `ju.env_..._feature` element.
    """
    body = "".join(f"<app:{tag}>{value}</app:{tag}>" for tag, value in tags_values)
    gml = f"""<?xml version="1.0" encoding="UTF-8"?>
<msGMLOutput xmlns:gml="http://www.opengis.net/gml"
             xmlns:app="http://example.com/app">
  <app:some_layer>
    <app:some_layer_feature>
      {body}
    </app:some_layer_feature>
  </app:some_layer>
</msGMLOutput>"""

    features = parse_wms_getfeatureinfo(
        gml.encode("utf-8"), "application/vnd.ogc.gml", {"name": "XX"}
    )

    expected = dict(tags_values)
    assert features == [expected]


# --- Observed pattern 3a: process_ground_category with property_values ---


@given(
    property_name=safe_tag_name,
    entries=st.lists(
        st.tuples(
            safe_text_value, st.integers(min_value=1, max_value=3), safe_text_value
        ),
        min_size=1,
        max_size=4,
        unique_by=lambda e: e[0],
    ),
)
@settings(max_examples=25)
def test_process_ground_category_property_values_matching_preserved(
    property_name, entries
):
    """For a layer configured with property_values (no bbox_zones), a feature
    whose attribute matches a configured name contributes that entry's
    target_harmonized_value, and the final harmonized_value is the max of all
    matched values -- exactly as observed today for cantons like JU/GE.
    """
    property_values = [
        {"name": name, "target_harmonized_value": target, "desc": desc}
        for name, target, desc in entries
    ]
    config_layers = [
        {
            "name": "test_layer",
            "property_name": property_name,
            "property_values": property_values,
        }
    ]
    # One feature per configured entry, each a genuine match.
    ground_features = [{property_name: name} for name, _target, _desc in entries]

    result = process_ground_category(ground_features, config_layers)

    expected_max = max(target for _name, target, _desc in entries)
    assert result.harmonized_value == expected_max
    matched_descs = result.source_values.split(",") if result.source_values else []
    for _name, _target, desc in entries:
        assert desc in matched_descs


@given(
    property_name=safe_tag_name,
    configured_name=safe_text_value,
    target=st.integers(min_value=1, max_value=3),
    unmatched_value=safe_text_value,
)
@settings(max_examples=25)
def test_process_ground_category_property_values_no_match_falls_back_to_unknown(
    property_name, configured_name, target, unmatched_value
):
    """When no feature's attribute matches any configured property_value
    name, harmonized_value falls back to 4 (UNKNOWN) with empty
    source_values -- exactly as observed today (test_processing.py's
    test_process_ground_category_no_matching_features).
    """
    if unmatched_value == configured_name:
        unmatched_value += "_x"

    config_layers = [
        {
            "name": "test_layer",
            "property_name": property_name,
            "property_values": [
                {
                    "name": configured_name,
                    "target_harmonized_value": target,
                    "desc": "d",
                }
            ],
        }
    ]
    ground_features = [{property_name: unmatched_value}]

    result = process_ground_category(ground_features, config_layers)

    assert result.harmonized_value == 4
    assert result.source_values == ""


# --- Observed pattern 3b: process_ground_category with layer-presence matching ---


@given(
    property_name=safe_tag_name,
    target_value=st.integers(min_value=1, max_value=3),
    matches=st.booleans(),
)
@settings(max_examples=25)
def test_process_ground_category_layer_presence_matching_preserved(
    property_name, target_value, matches
):
    """For a layer with no property_values, matching is purely by comparing
    the layer's property_name against the feature's layerName; a match
    contributes the layer-level target_harmonized_value, exactly as observed
    today (test_processing.py's test_process_ground_category_layer_name_matching).
    """
    layer_cfg = {
        "name": "layer",
        "property_name": property_name,
        "property_values": None,
        "target_harmonized_value": target_value,
    }
    layer_name = property_name if matches else f"{property_name}_other"
    ground_features = [{"layerName": layer_name}]

    result = process_ground_category(ground_features, [layer_cfg])

    assert result.harmonized_value == (target_value if matches else 4)


# --- Observed pattern 4: QUERY_LAYERS identical to LAYERS (no queryable: false) ---


@given(
    canton_code=non_zh_canton_code,
    layer_names=st.lists(safe_tag_name, min_size=1, max_size=5, unique=True),
)
# deadline=None: each example performs a real (mocked) HTTP round trip via
# respx/httpx, which routinely exceeds hypothesis's default 200ms deadline on
# this machine; the property itself is deterministic and has nothing to do
# with timing.
@settings(max_examples=15, deadline=None)
def test_query_layers_equals_layers_without_queryable_false(canton_code, layer_names):
    """fetch_features_for_point's WMS branch builds QUERY_LAYERS as the exact
    same comma-joined list as LAYERS, for any canton config whose layers have
    no `queryable: false` entry (every canton today, since the field doesn't
    exist yet) -- observed directly against the current implementation.
    """
    config = {
        "name": canton_code,
        "info_format": "application/vnd.ogc.gml",
        "bbox_delta": 10,
        "query_url": "https://example.test/wms",
        "layers": [{"name": n} for n in layer_names],
        "style": "",
    }
    minimal_gml = (
        b"<wfs:FeatureCollection xmlns:wfs='http://www.opengis.net/wfs' "
        b"xmlns:gml='http://www.opengis.net/gml'></wfs:FeatureCollection>"
    )

    with respx.mock:
        respx.get(config["query_url"]).mock(
            return_value=httpx.Response(
                200,
                content=minimal_gml,
                headers={"Content-Type": "application/vnd.ogc.gml"},
            )
        )
        result = asyncio.run(fetch_features_for_point(2600000, 1200000, config))

    query = parse_qs(urlparse(result["full_url"]).query)
    query_layers = query.get("QUERY_LAYERS", [""])[0]
    layers_param = query.get("LAYERS", [""])[0]
    expected = ",".join(layer_names)

    assert query_layers == expected
    assert layers_param == expected
    assert query_layers == layers_param


# --- Observed pattern 5: transport-level failures -> geoservice_unavailable ---


def _minimal_wms_config(canton_code: str) -> dict:
    return {
        "name": canton_code,
        "info_format": "application/vnd.ogc.gml",
        "bbox_delta": 10,
        "query_url": "https://example.test/wms",
        "layers": [{"name": "some_layer"}],
        "style": "",
    }


@pytest.mark.parametrize("canton_code", ["ZH", "JU"])
@pytest.mark.parametrize(
    "mock_kwargs",
    [
        {"side_effect": httpx.ConnectTimeout("Connection timed out")},
        {"side_effect": httpx.ConnectError("Connection refused")},
        {"return_value": httpx.Response(404, text="Not Found")},
        {"return_value": httpx.Response(500, text="Internal Server Error")},
    ],
    ids=["timeout", "connect_error", "http_404", "http_500"],
)
@respx.mock
def test_transport_failures_return_geoservice_unavailable(canton_code, mock_kwargs):
    """WMS transport-level failures (timeout, connection error, 4xx, 5xx)
    continue to return `geoservice_unavailable: True` with empty features,
    for both ZH and non-ZH cantons -- unaffected by the ZH-specific fix since
    the failure is caught before any canton-specific parsing runs.
    """
    config = _minimal_wms_config(canton_code)
    respx.get(config["query_url"]).mock(**mock_kwargs)

    result = asyncio.run(fetch_features_for_point(2600000, 1200000, config))

    assert result["features"] == []
    assert result.get("geoservice_unavailable") is True
    assert result["error"] is not None
