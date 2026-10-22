# Implementation Plan

## Overview

This plan implements the fix described in `design.md` for the ZH canton drill-category bug: it
replaces the seven-layer `ZH.yaml` configuration (six stale per-zone layer names plus a
non-queryable `erdwaermesonden-auflagen` layer) with the single real, queryable
`waermenutzung-zonen` layer resolved via a static bounding-box lookup (`bbox_zones`), adds the
supporting `queryable`/`bbox_zones` schema fields, updates `processing.py`'s WMS request
building, GML parsing, and category resolution accordingly, and validates the fix with
exploration, preservation, and integration tests. Per the user's explicit decision, the
`erdwaermesonden-auflagen` restriction itself remains undetectable and out of scope for this fix;
ground control point 1 ("Auflagen & waermenutzung-zone-d") is left with its documented expected
value of `3` unchanged in `ZH.yaml`, and the final integration test explicitly asserts that this
control point does NOT match its expected value after the fix, to document the known gap rather
than hide it.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - ZH stale/non-queryable layers return empty features
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **GOAL**: Surface counterexamples that demonstrate the three root causes from design.md
    (stale per-zone layer names, non-queryable `erdwaermesonden-auflagen`, attribute-less
    `waermenutzung-zonen` response)
  - **Scoped PBT Approach**: The bug is deterministic for any ZH coordinate under the current
    `ZH.yaml`, so scope the property to the concrete failing fixtures instead of random
    generation:
    1. Feed a recorded `ServiceExceptionReport` (`LayerNotDefined`) body through
       `parse_wms_getfeatureinfo` with `config={"name": "ZH"}` — assert it returns `[]`
    2. Feed a recorded attribute-less `waermenutzung-zonen` GML response
       (`gml:boundedBy`/`gml:Box`, no `gml:name`) through `parse_wms_getfeatureinfo` with
       `config={"name": "ZH"}` — assert it returns `[]` (the current `gml:name` special case
       cannot recover zone identity even with the correct layer name)
    3. Feed a recorded `erdwaermesonden-auflagen`-only `ServiceExceptionReport` through the
       unfixed pipeline — assert fallback to `harmonized_value=4`
  - Test implementation details from Bug Condition in design.md (`isBugCondition`: any
    coordinate resolving to canton `ZH` under the unfixed `ZH.yaml` layer list)
  - The test assertions should match the Expected Behavior Properties from design.md (Property
    1: `QUERY_LAYERS` contains only `waermenutzung-zonen`, no `ServiceExceptionReport`-driven
    empty-feature fallback, `harmonized_value` resolved via `bbox_zones` instead of UNKNOWN(4))
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS / confirms empty features and `harmonized_value=4` (this is
    correct — it proves the bug exists)
  - Document counterexamples found, e.g. "`parse_wms_getfeatureinfo` on the
    `ServiceExceptionReport` fixture returns `[]`", "`waermenutzung-zonen`'s bbox-only response
    also returns `[]` even with the correct layer name", "`erdwaermesonden-auflagen` alone
    returns `[]` because it is `queryable=0`"
  - Mark task complete when test is written, run, and failure/counterexamples are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - non-ZH parsing and processing behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code:
    - `parse_wms_getfeatureinfo` with a `gml:featureMember` response (e.g. the existing JU
      fixture `tests/data/wms/getfeatureinfo_ju.gml`) returns the same feature dicts as today
    - `parse_wms_getfeatureinfo` with a MapServer `*_feature` (`msGMLOutput`) response returns
      the same feature dicts as today
    - `process_ground_category` for a layer with `property_values` (no `bbox_zones`) and for a
      layer using layer-presence matching (no `property_values`) returns the same
      `harmonized_value`/`source_values` as today
    - `fetch_features_for_point`'s WMS branch builds `QUERY_LAYERS` identical to `LAYERS` for
      every canton config that has no `queryable: false` entries (i.e. every canton except ZH)
    - Transport-level failures (timeout, 4xx/5xx, connection error) return
      `geoservice_unavailable` for both ZH and non-ZH cantons
  - Write property-based tests capturing these observed patterns from the Preservation
    Requirements in design.md: "for all non-ZH inputs (or ZH inputs where the request fails at
    the HTTP transport level), the fixed code produces exactly the same result as the original
    code"
  - Generate random `Layer`-shaped configs (varying `property_values`, layer-presence-only
    configs, and canton name) that never set `bbox_zones`/`queryable: false`, and assert
    `process_ground_category`/`fetch_features_for_point` behavior is byte-identical to the
    pre-fix implementation for all of them
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for ZH canton drill-category always resolving to UNKNOWN(4)

  - [x] 3.1 Add `queryable` and `bbox_zones`/`BboxZone` schema fields
    - In `src/drillapi/cantons_configuration/schema.py`, add `queryable: bool = True` to `Layer`
      (generic, default-safe — every existing canton is unaffected since the default is `True`)
    - Add a new `BboxZone` model (`extra="forbid"`) with `bbox: list[float]` (length 4),
      `name: str`, `target_harmonized_value: GroundSuitability`, `desc: str | None = None`
    - Add `bbox_zones: list[BboxZone] | None = None` to `Layer` (ZH-only, additive)
    - _Bug_Condition: isBugCondition(input) from design.md — canton resolves to ZH_
    - _Expected_Behavior: expectedBehavior(result) from design.md Correctness Properties_
    - _Requirements: 2.1, 2.2_

  - [x] 3.2 Consolidate ZH.yaml to the real queryable layer plus bbox_zones
    - In `src/drillapi/cantons_configuration/data/ZH.yaml`, replace the seven-layer list with two
      layers:
      - `erdwaermesonden-auflagen`: keep `property_values` as-is, add `queryable: false`
      - `waermenutzung-zonen` (replacing the six `waermenutzung-zone-a`..`-f` entries): add
        `bbox_zones` with one entry per zone (A–F), each `bbox` set to the live `gml:Box`
        coordinates observed for that zone's documented `ground_control_point` (record Zones
        A/B/C from the design.md investigation findings; query D/E/F the same way); carry over
        `name`/`target_harmonized_value`/`desc` unchanged from today's per-zone layer entries
    - Leave every `ground_control_point` entry's expected value unchanged, including control
      point 1 (`2677790, 1260185`, "Auflagen & waermenutzung-zone-d", expected `3`) — do NOT
      change it to `2`; its mismatch after the fix is a documented, known gap (see task 4), not
      something to be "fixed" by relabeling the fixture data
    - _Bug_Condition: isBugCondition(input) from design.md — canton resolves to ZH_
    - _Expected_Behavior: expectedBehavior(result) from design.md Correctness Properties_
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Build separate QUERY_LAYERS/LAYERS lists in fetch_features_for_point
    - In `src/drillapi/services/processing.py`, in the WMS branch of `fetch_features_for_point`,
      build `layers_list` (all layer names, used for `LAYERS`) and `query_layers_list` (only
      layers where `layer.get("queryable", True)` is `True`, used for `QUERY_LAYERS`)
    - Non-ZH cantons have no `queryable: false` entries, so `query_layers_list == layers_list`
      for them — zero behavior change
    - _Bug_Condition: isBugCondition(input) from design.md — canton resolves to ZH_
    - _Expected_Behavior: expectedBehavior(result) from design.md — QUERY_LAYERS contains only
      waermenutzung-zonen for ZH_
    - _Preservation: Preservation Requirements from design.md — QUERY_LAYERS/LAYERS construction
      unchanged for every canton without queryable: false_
    - _Requirements: 2.1, 3.4_

  - [x] 3.4 Replace ZH's gml:name special case with bbox extraction
    - In `parse_wms_getfeatureinfo`, replace the ZH-specific `gml:name` lookup (gated on
      `config["name"] == "ZH"`) with a `gml:boundedBy/gml:Box` extraction, appending
      `{"bbox": coords}` to `features` when found
    - Add a `_parse_gml_box(box_elem, ns)` helper that reads the `gml:coordinates` (or
      `gml:coord`/`gml:pos` pairs, depending on GML version) inside the `gml:Box` and returns a
      4-element float list (`[minx, miny, maxx, maxy]`), returning `None` on any malformed input
      so parsing failures degrade to "no feature" rather than a crash
    - This branch is gated on `config["name"] == "ZH"`, so no other canton's parsing path is
      touched
    - _Bug_Condition: isBugCondition(input) from design.md — canton resolves to ZH_
    - _Expected_Behavior: expectedBehavior(result) from design.md — resolves a feature with a
      bbox instead of an empty feature list_
    - _Preservation: Preservation Requirements from design.md — gml:featureMember / *_feature
      extraction unchanged for every canton_
    - _Requirements: 2.1, 2.2, 3.1, 3.2_

  - [x] 3.5 Add bbox_zones matching branch to process_ground_category
    - In `process_ground_category`, read `bbox_zones = layer_cfg.get("bbox_zones")` and, when
      present, evaluate it before the existing `property_values` branch: for each feature with a
      `bbox`, compare against each zone's `bbox` and, on a match, append the zone's
      `target_harmonized_value`/`desc` to `mapped_values`/`source_values`
    - Add a `_bbox_matches(a, b, tolerance=0.5)` helper comparing all four coordinates with
      `math.isclose`/absolute tolerance (meters, EPSG:2056)
    - This branch is purely additive: layers without `bbox_zones` fall through to the existing
      `property_values` / layer-presence logic unchanged
    - _Bug_Condition: isBugCondition(input) from design.md — canton resolves to ZH_
    - _Expected_Behavior: expectedBehavior(result) from design.md — harmonized_value resolves to
      the matched zone's target_harmonized_value instead of falling back to UNKNOWN(4)_
    - _Preservation: Preservation Requirements from design.md — property_values / layer-presence
      matching unchanged for every layer without bbox_zones_
    - _Requirements: 2.1, 2.2, 2.3, 3.3_

  - [x] 3.6 Update existing ZH-specific unit tests for the new bbox-based extraction
    - Rewrite `test_parse_zh_special_case` and `test_parse_zh_no_name_element` in
      `tests/test_processing.py` to feed `gml:boundedBy`/`gml:Box` fixtures (present and
      malformed/missing) instead of `gml:name`, asserting a single `{"bbox": [...]}` feature and
      an empty feature list respectively
    - This is an intentional replacement of ZH-only test behavior, not a regression under
      requirements 3.1–3.4 (those requirements cover non-ZH canton logic and transport-level
      failures only)
    - _Preservation: Preservation Requirements from design.md — this change is scoped to the
      ZH-only special case and does not affect non-ZH preservation guarantees_
    - _Requirements: 2.1, 2.2_

  - [x] 3.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - ZH zone resolution via bounding-box lookup
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior (QUERY_LAYERS limited to
      `waermenutzung-zonen`, bbox-based feature extraction, bbox_zones-based harmonized_value
      resolution)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from task 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms the bug is fixed for the scoped failing cases)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.8 Verify preservation tests still pass
    - **Property 2: Preservation** - non-ZH parsing and processing behavior
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from task 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions for non-ZH cantons and
      transport-level failure handling)
    - Confirm all tests still pass after the fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Write ZH integration test documenting the known Auflagen gap
  - Replay `fetch_features_for_point`/`process_ground_category` (or the full
    `/v1/drill-category/{coord_x}/{coord_y}` route) against recorded fixtures for all 6
    documented `ZH.yaml` `ground_control_point` entries
  - For the 5 zone-only control points (Zone A: `2688561,1274977` expected `3`; Zone B:
    `2681563,1248410` expected `2`; Zone C: `2680649,1246765` expected `2`; Zone D:
    `2692350,1275334` expected `2`; Zone E: `2693733,1238583` expected `2`), assert the resulting
    `harmonized_value` MATCHES each entry's documented expected value after the fix
  - For control point 1 (`2677790,1260185`, "Auflagen & waermenutzung-zone-d", documented
    expected `3`), assert the resulting `harmonized_value` does **NOT** match `3` (it resolves to
    Zone D's bbox-matched value of `2` instead) — this explicitly documents the known,
    out-of-scope gap from design.md's Correctness Properties (the `erdwaermesonden-auflagen`
    restriction is not detectable by this fix since the layer is non-queryable) rather than
    letting the mismatch pass or fail silently. Add a comment in the test explaining why this
    assertion is inverted and referencing the follow-up bugfix that would need to address it
  - Add a full-route test for a representative non-ZH canton coordinate (e.g. the existing
    JU/FR fixtures) asserting the response is unchanged from the current baseline
  - _Requirements: 2.3, 3.1, 3.2, 3.3, 3.4_

- [x] 5. Checkpoint - Ensure all tests pass
  - Run the full test suite (`pytest`) and confirm:
    - The bug condition exploration test (task 1 / 3.7) passes
    - The preservation tests (task 2 / 3.8) pass
    - The new ZH integration test (task 4) passes, including its inverted assertion for control
      point 1
    - `test_configuration_structure.py` still validates `ZH.yaml` against the updated schema
  - Ask the user if questions arise

## Task Dependency Graph

```
1. Write bug condition exploration test
2. Write preservation property tests
   (1 and 2 are independent of each other, both must precede 3)

3. Fix for ZH canton drill-category always resolving to UNKNOWN(4)
  3.1 Add queryable and bbox_zones/BboxZone schema fields
    -> 3.2 Consolidate ZH.yaml to the real queryable layer plus bbox_zones (needs bbox_zones field)
    -> 3.3 Build separate QUERY_LAYERS/LAYERS lists (needs queryable field)
  3.3 -> 3.4 Replace ZH's gml:name special case with bbox extraction
  3.4 -> 3.5 Add bbox_zones matching branch to process_ground_category (needs bbox features)
  3.2, 3.5 -> 3.6 Update existing ZH-specific unit tests
  3.2..3.6 -> 3.7 Verify bug condition exploration test now passes (re-runs task 1's test)
  3.2..3.6 -> 3.8 Verify preservation tests still pass (re-runs task 2's tests)

4. Write ZH integration test documenting the known Auflagen gap (depends on 3.7, 3.8 passing)
5. Checkpoint - Ensure all tests pass (depends on 1, 2, 3.7, 3.8, 4)
```

```json
{
  "waves": [
    ["1", "2"],
    ["3.1"],
    ["3.2", "3.3"],
    ["3.4"],
    ["3.5"],
    ["3.6"],
    ["3.7", "3.8"],
    ["4"],
    ["5"]
  ]
}
```

## Notes

- The open question flagged in `design.md` (whether to update ground control point 1's expected
  value) was resolved by the user: leave it as-is (`3`) in `ZH.yaml`, documented as a known gap.
  Detecting the `erdwaermesonden-auflagen` restriction is explicitly out of scope for this fix and
  is deferred to a separate, future bugfix.
- `bbox_zones` coordinates for Zones D, E, F must be recorded during task 3.2 by querying the live
  `waermenutzung-zonen` layer at each zone's documented `ground_control_point`, following the same
  approach already used for Zones A/B/C in the design investigation.
