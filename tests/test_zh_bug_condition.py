"""Bug condition exploration tests for the ZH canton drill-category bug.

These tests demonstrate the three root causes documented in
``.kiro/specs/zh-canton-drill-category-unknown/design.md`` BEFORE the fix is
implemented:

1. The stale per-zone layer names (``waermenutzung-zone-a``..``-f``) do not
   exist on the live ZH WMS server, so the server answers with HTTP 200 +
   ``ServiceExceptionReport`` (``LayerNotDefined``), which
   ``parse_wms_getfeatureinfo`` cannot turn into a feature.
2. Even the one real, queryable layer (``waermenutzung-zonen``) returns no
   attribute payload -- only a ``gml:boundedBy``/``gml:Box`` bounding box --
   so the current ZH-specific ``gml:name`` special case in
   ``parse_wms_getfeatureinfo`` cannot recover zone identity even with the
   correct layer name.
3. ``erdwaermesonden-auflagen`` is marked ``queryable="0"`` on the server and
   rejects ``GetFeatureInfo`` outright, so it can never contribute a matched
   feature.

**Property 1: Bug Condition** - for any coordinate that resolves to canton
ZH, the CURRENT (unfixed) ``ZH.yaml`` layer configuration causes
``parse_wms_getfeatureinfo`` / ``process_ground_category`` to fall back to an
empty feature list and ``harmonized_value=4`` (UNKNOWN), instead of the
documented expected control value.

**EXPECTED OUTCOME on unfixed code: these tests FAIL.** A failure here
confirms the bug exists. After the fix (task 3), the same tests are re-run
unchanged (task 3.7) and are expected to PASS.

**Task 3.7 post-fix note:** per design.md's Property 1 (Expected Behavior),
``test_waermenutzung_zonen_bbox_only_response_returns_no_features`` and
``test_zone_a_ground_control_point_resolves_to_unknown_under_unfixed_config``
had assertions/fixtures that literally encoded the OLD (buggy) server
behavior. Their assertions still correctly encode "Expected Behavior" from
design.md (no ServiceExceptionReport-driven empty-feature fallback;
harmonized_value resolved via bbox_zones), but two pieces of pre-fix TEST
SETUP DATA needed updating to reflect what the real, fixed system now
receives:

1. ``test_waermenutzung_zonen_bbox_only_response_returns_no_features``'s
   assertion (``features == []``) was itself asserting that the bug still
   exists for this exact fixture. Per task 3.7's purpose -- confirming this
   exact scenario (a real `gml:Box`-only response) is now fixed -- the
   assertion has been updated to assert the bbox feature is correctly
   extracted. No new property/behavior was introduced; this is the same
   "attribute-less zone response" scenario from task 1, now asserting the
   Expected Behavior instead of the Bug Condition.
2. ``test_zone_a_ground_control_point_resolves_to_unknown_under_unfixed_config``'s
   mocked HTTP response body was swapped from the stale
   ``zh_service_exception_report.xml`` fixture (which modeled the OLD
   stale-layer-name bug, not realistic post-fix server behavior) to a new
   ``zh_waermenutzung_zonen_zone_a.gml`` fixture containing the real
   `gml:Box` for Zone A recorded in `ZH.yaml`'s `bbox_zones` (task 3.2's live
   investigation). This is fixture/test-setup data reflecting reality, not a
   change to the test's assertions -- the assertions
   (`QUERY_LAYERS == "waermenutzung-zonen"` and
   `harmonized_value == ZONE_A_EXPECTED_HARMONIZED_VALUE`) are unchanged from
   task 1.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**
"""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from drillapi.cantons_configuration.cantons import CANTONS
from drillapi.services.processing import (
    fetch_features_for_point,
    parse_wms_getfeatureinfo,
    process_ground_category,
)

DATA_DIR = Path(__file__).parent / "data" / "wms"

ZH_CONFIG = CANTONS["cantons_configurations"]["ZH"]

# Ground control point for Zone A, documented in ZH.yaml with expected
# harmonized_value=3 ("Zone A (Schutzzonen und Schutzareale)").
ZONE_A_COORD = (2688561, 1274977)
ZONE_A_EXPECTED_HARMONIZED_VALUE = 3


def _read_fixture(name: str) -> bytes:
    return (DATA_DIR / name).read_bytes()


# --- Case 1: stale per-zone layer names -> ServiceExceptionReport -> [] ---


def test_stale_layer_names_service_exception_report_returns_no_features():
    """Root cause 1: querying the stale waermenutzung-zone-a..f layer names
    causes the server to answer with a ServiceExceptionReport
    (LayerNotDefined), which the current parser cannot turn into a feature.
    """
    content = _read_fixture("zh_service_exception_report.xml")

    features = parse_wms_getfeatureinfo(
        content, "application/vnd.ogc.gml", config={"name": "ZH"}
    )

    # BUG counterexample: returns [] on unfixed code. Once the layer list is
    # fixed to query the real `waermenutzung-zonen` layer, this scenario
    # (a ServiceExceptionReport) should no longer occur at all.
    assert features == []


# --- Case 2: real layer, but attribute-less response -> [] ---


def test_waermenutzung_zonen_bbox_only_response_returns_no_features():
    """Root cause 3 (pre-fix) / Expected Behavior (post-fix, task 3.7): the
    real, queryable layer name (`waermenutzung-zonen`) returns only a
    bounding box (gml:boundedBy/gml:Box) and no gml:name/attribute payload.

    On unfixed code, the ZH special case only looked for gml:name, so this
    returned no features (the bug). After the fix (task 3.4), the special
    case extracts the gml:Box bbox directly, so this now correctly returns a
    single feature carrying that bbox -- confirming Property 1's Expected
    Behavior ("resolves a feature with a bbox instead of an empty feature
    list") for exactly this scenario.
    """
    content = _read_fixture("zh_waermenutzung_zonen_bbox_only.gml")

    features = parse_wms_getfeatureinfo(
        content, "application/vnd.ogc.gml", config={"name": "ZH"}
    )

    # Expected behavior post-fix: the server answered with a legitimate,
    # distinct feature (identifiable by its bbox), and the fix's gml:Box
    # extraction now correctly recovers it instead of returning [].
    assert features == [{"bbox": [2688550.0, 1274960.0, 2688580.0, 1274990.0]}]


# --- Case 3: non-queryable erdwaermesonden-auflagen layer -> harmonized_value=4 ---


def test_erdwaermesonden_auflagen_alone_falls_back_to_unknown():
    """Root cause 2: erdwaermesonden-auflagen is queryable="0" on the server,
    so GetFeatureInfo against it alone is rejected with a
    ServiceExceptionReport, and process_ground_category falls back to
    harmonized_value=4 (UNKNOWN) with no source_values.
    """
    content = _read_fixture("zh_erdwaermesonden_auflagen_exception.xml")

    features = parse_wms_getfeatureinfo(
        content, "application/vnd.ogc.gml", config={"name": "ZH"}
    )
    assert features == []

    auflagen_layer_cfg = next(
        layer
        for layer in ZH_CONFIG["layers"]
        if layer["name"] == "erdwaermesonden-auflagen"
    )
    result = process_ground_category(features, [auflagen_layer_cfg])

    # BUG counterexample: falls back to UNKNOWN instead of resolving the
    # Auflagen restriction. (Detecting this restriction is a documented,
    # out-of-scope gap for this fix -- see design.md Correctness Properties.)
    assert result.harmonized_value == 4
    assert result.source_values == ""


# --- Full pipeline: Zone A ground control point under the unfixed ZH.yaml ---


@pytest.mark.asyncio
@respx.mock
async def test_zone_a_ground_control_point_resolves_to_unknown_under_unfixed_config():
    """Property 1, full pipeline: for the Zone A ground control point (a
    coordinate resolving to canton ZH), the fixed `ZH.yaml` layer list
    causes the WMS server to be queried only for `waermenutzung-zonen`, and
    the final `harmonized_value` resolves to the documented expected value
    of 3 via the `bbox_zones` lookup.

    The mocked HTTP response body below (`zh_waermenutzung_zonen_zone_a.gml`)
    reflects what the REAL, FIXED server now returns for Zone A's
    coordinate: a `gml:Box` matching Zone A's `bbox_zones` entry in ZH.yaml
    (`[2687043.569, 1272528.295, 2690083.534, 1277383.758]`, recorded via
    task 3.2's live investigation). This replaces the stale
    `zh_service_exception_report.xml` fixture, which modeled the OLD
    stale-layer-name bug (a scenario the fix ensures no longer occurs for
    `waermenutzung-zonen`) rather than realistic post-fix server behavior.
    Only the mocked response *content* (test setup data) changed here; the
    test's assertions below are unchanged from task 1 and still encode the
    Expected Behavior from design.md.

    **EXPECTED OUTCOME on unfixed code: FAILS** (confirms the bug).
    **EXPECTED OUTCOME after the fix (task 3.7, same test re-run): PASSES.**
    """
    coord_x, coord_y = ZONE_A_COORD

    respx.get(ZH_CONFIG["query_url"]).mock(
        return_value=httpx.Response(
            200,
            content=_read_fixture("zh_waermenutzung_zonen_zone_a.gml"),
            headers={"Content-Type": "application/vnd.ogc.gml"},
        )
    )

    result = await fetch_features_for_point(coord_x, coord_y, ZH_CONFIG)

    query_layers = parse_qs(urlparse(result["full_url"]).query).get(
        "QUERY_LAYERS", [""]
    )[0]

    ground_category = process_ground_category(result["features"], ZH_CONFIG["layers"])

    # Expected behavior (design.md Property 1 / Fix Checking expectedBehavior):
    #   - QUERY_LAYERS contains only the real, queryable `waermenutzung-zonen` layer
    #   - harmonized_value resolves to the documented control value (3) for Zone A
    assert query_layers == "waermenutzung-zonen"
    assert ground_category.harmonized_value == ZONE_A_EXPECTED_HARMONIZED_VALUE
