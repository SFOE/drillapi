"""Integration tests for the fixed ZH canton drill-category configuration.

These tests replay the full ``/v1/drill-category/{coord_x}/{coord_y}`` route
against recorded fixtures for all 6 documented ``ground_control_point``
entries in ``ZH.yaml``, confirming the fix (task 3) resolves each zone-only
control point to its documented expected ``harmonized_value`` via the new
``bbox_zones`` lookup.

Control point 1 ("Auflagen & waermenutzung-zone-d") is handled separately: as
documented in ``design.md``'s Correctness Properties and the Notes section of
``tasks.md``, detecting the ``erdwaermesonden-auflagen`` restriction is a
known, out-of-scope gap for this fix (the layer is ``queryable: false`` on
the live server and can never contribute a matched feature). That control
point's coordinate falls inside Zone D's bbox, so it resolves to Zone D's
``target_harmonized_value`` (``2``) instead of its documented expected value
of ``3``. The test below asserts this mismatch explicitly (rather than
asserting equality and leaving a silently-skipped gap) so a future change
that "accidentally" starts matching ``3`` again -- without an actual fix for
the Auflagen restriction -- would be caught as a surprising change in
behavior.

**Validates: Requirements 2.3, 3.1, 3.2, 3.3, 3.4**
"""

from pathlib import Path

import httpx
import pytest
import respx

DATA_DIR = Path(__file__).parent / "data"

ZH_QUERY_URL = "https://wms.zh.ch/AwelGSWaermewwwZHWMS"
GEOADMIN_URL = "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify"


def _read(relative: str) -> bytes:
    return (DATA_DIR / relative).read_bytes()


def _mock_zh_canton_identify():
    respx.get(GEOADMIN_URL).mock(
        return_value=httpx.Response(
            200,
            content=_read("geoadmin/canton_identify_zh.json"),
            headers={"Content-Type": "application/json"},
        )
    )


def _mock_zh_wms(gml_fixture: str):
    respx.get(ZH_QUERY_URL).mock(
        return_value=httpx.Response(
            200,
            content=_read(f"wms/{gml_fixture}"),
            headers={"Content-Type": "application/vnd.ogc.gml"},
        )
    )


# --- The 5 zone-only ground control points: fixed code matches the documented value ---

ZONE_ONLY_CONTROL_POINTS = [
    pytest.param(2688561, 1274977, "zh_waermenutzung_zonen_zone_a.gml", 3, id="zone_a"),
    pytest.param(2681563, 1248410, "zh_waermenutzung_zonen_zone_b.gml", 2, id="zone_b"),
    pytest.param(2680649, 1246765, "zh_waermenutzung_zonen_zone_c.gml", 2, id="zone_c"),
    pytest.param(2692350, 1275334, "zh_waermenutzung_zonen_zone_d.gml", 2, id="zone_d"),
    pytest.param(2693733, 1238583, "zh_waermenutzung_zonen_zone_e.gml", 2, id="zone_e"),
]


@pytest.mark.parametrize(
    "coord_x, coord_y, gml_fixture, expected_harmonized_value", ZONE_ONLY_CONTROL_POINTS
)
@respx.mock
def test_zone_only_ground_control_point_matches_expected_value(
    client, coord_x, coord_y, gml_fixture, expected_harmonized_value
):
    """For the 5 zone-only ground control points, the full route resolves
    `harmonized_value` to the documented expected control value, via the
    `bbox_zones` lookup matching the recorded live bounding box for that
    zone.
    """
    _mock_zh_canton_identify()
    _mock_zh_wms(gml_fixture)

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canton"] == "ZH"
    assert payload["ground_category"]["harmonized_value"] == expected_harmonized_value
    assert payload["ground_category"]["source_values"] != ""


# --- Control point 1: documented, known Auflagen gap ---


@respx.mock
def test_control_point_1_auflagen_zone_d_does_not_match_documented_expected_value(
    client,
):
    """Control point 1 (`2677790, 1260185`, "Auflagen & waermenutzung-zone-d")
    is documented in ZH.yaml with an expected `harmonized_value` of `3`
    (the "Auflagen fuer Erdwaermesonden" restriction, i.e. "Verbot").

    This fix cannot detect that restriction: `erdwaermesonden-auflagen` is
    marked `queryable: false` because the live ZH server rejects
    `GetFeatureInfo` against it outright (see design.md's Hypothesized Root
    Cause #2 and Correctness Properties' "Known, documented exclusion from
    scope"). The coordinate falls inside Zone D's bbox, so only the
    `waermenutzung-zonen` layer contributes a result, resolving
    `harmonized_value` to Zone D's `target_harmonized_value` (`2`) instead.

    **This assertion is intentionally inverted** (asserting the result does
    NOT equal the documented expected value of 3, rather than asserting it
    does) to explicitly document this known, out-of-scope gap rather than
    letting a silent mismatch pass uncommented or fail the suite outright.
    A follow-up bugfix scoped to the `erdwaermesonden-auflagen` restriction
    (see tasks.md's Notes: "is deferred to a separate, future bugfix") would
    need to make this resolve to `3` -- at which point this test's assertion
    should be flipped back to equality.
    """
    coord_x, coord_y = 2677790, 1260185
    documented_expected_value = 3

    _mock_zh_canton_identify()
    # The live server returns Zone D's bbox for this coordinate (it
    # geographically falls inside Zone D) -- there is no separate "Auflagen"
    # feature the zone-only layer could ever return.
    _mock_zh_wms("zh_waermenutzung_zonen_zone_d.gml")

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canton"] == "ZH"
    # Known gap: resolves to Zone D's value (2), NOT the documented Auflagen
    # value (3). See docstring above.
    assert payload["ground_category"]["harmonized_value"] != documented_expected_value
    assert payload["ground_category"]["harmonized_value"] == 2


# --- Non-ZH baseline: response unchanged by the ZH-scoped fix ---


@respx.mock
def test_non_zh_canton_baseline_unchanged(client):
    """A representative non-ZH canton (JU) full-route response is unchanged
    from the current baseline. The ZH fix is entirely gated on
    `config["name"] == "ZH"` / the additive `bbox_zones`/`queryable` fields,
    so JU (which has neither) must behave identically.

    This duplicates (deliberately, as a direct regression guard for this
    bugfix) the assertions already covered by
    `tests/test_drill_suitability.py::test_drill_category_wms_gml`.
    """
    coord_x, coord_y = 2574738, 1249285

    respx.get(GEOADMIN_URL).mock(
        return_value=httpx.Response(
            200,
            content=_read("geoadmin/canton_identify_ju.json"),
            headers={"Content-Type": "application/json"},
        )
    )
    respx.get("https://geoservices.jura.ch/wms").mock(
        return_value=httpx.Response(
            200,
            content=_read("wms/getfeatureinfo_ju.gml"),
            headers={"Content-Type": "application/vnd.ogc.gml"},
        )
    )

    response = client.get(f"/v1/drill-category/{coord_x}/{coord_y}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canton"] == "JU"
    assert payload["ground_category"]["harmonized_value"] == 1
    assert payload["result_detail"]["detail"] is None
