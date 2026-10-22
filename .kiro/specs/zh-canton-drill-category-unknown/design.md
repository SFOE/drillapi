# ZH Canton Drill Category Unknown Bugfix Design

## Overview

The ZH (Zürich) canton integration always returns `harmonized_value=4` (UNKNOWN) because `ZH.yaml`
queries seven WMS layer names, six of which (`waermenutzung-zone-a` .. `waermenutzung-zone-f`) do not
exist on the live server, and a seventh (`erdwaermesonden-auflagen`) is marked `queryable="0"` by the
server's `GetCapabilities`. Live investigation (see "Investigation Findings" below) confirmed:

- The server only publishes one real, queryable zone layer: `waermenutzung-zonen`.
- `GetFeatureInfo` against `waermenutzung-zonen` returns a feature with **no attribute payload at
  all** — only a `gml:boundedBy` bounding box (`gml:Box`) — for every tested `INFO_FORMAT`
  (GML2/GML3/text/plain). JSON/HTML are rejected outright by the server.
- No alternate endpoint (WFS, ArcGIS REST/FeatureServer, or real per-zone layers) exists that exposes
  zone identity as a readable attribute.
- `erdwaermesonden-auflagen` cannot be queried via `GetFeatureInfo` under any combination tested; the
  server rejects it with `LayerNotDefined` / "not offered by the service instance" whenever it appears
  in `QUERY_LAYERS`.

Because no attribute data is available, the fix resolves zone identity from the **bounding box** that
`waermenutzung-zonen` returns, matched against a static bbox→zone lookup table recorded once (via the
documented `ground_control_point` entries) and stored in `ZH.yaml`. `erdwaermesonden-auflagen` is kept
in the WMS `LAYERS` parameter (so the request shape matches the real service) but removed from
`QUERY_LAYERS`, since the server never answers queries against it; its contribution to
`harmonized_value` is documented as a known, out-of-scope limitation rather than silently claimed as
fixed.

The fix is scoped entirely to the ZH canton: the ZH-specific branch of `parse_wms_getfeatureinfo`, a
new ZH-only `bbox_zones` matching branch in `process_ground_category`, `ZH.yaml`, and two small,
backward-compatible schema additions (`Layer.queryable`, `Layer.bbox_zones`) whose defaults preserve
behavior for every other canton untouched.

### Investigation Findings (incorporated, not re-derived)

- `GetCapabilities` for `https://wms.zh.ch/AwelGSWaermewwwZHWMS` lists `waermenutzung-zonen`
  (`queryable="1"`) and `erdwaermesonden-auflagen` (`queryable="0"`) as the only relevant layers. No
  `waermenutzung-zone-a`..`-f` layers exist. No WFS/ArcGIS REST alternative exists (WFS requests on the
  same base URL return "WFS request not enabled").
- Live `GetFeatureInfo` against `waermenutzung-zonen` for 3 documented ground control points (Zone A,
  B, C) returned only a `gml:boundedBy` bounding box per feature, differing per point (proving a
  distinct feature was matched each time) but with no zone letter, name, or category attribute in any
  tested `INFO_FORMAT`.
- `erdwaermesonden-auflagen` rejects `GetFeatureInfo` outright even when queried alone.

## Glossary

- **Bug_Condition (C)**: The condition under which the ZH integration returns an incorrect result —
  any request for a coordinate that resolves to canton ZH, evaluated against the current (unfixed)
  `ZH.yaml` layer configuration.
- **Property (P)**: The desired behavior for ZH requests — the system queries only real, queryable
  layer names, resolves the zone-layer's bounding box to the correct `target_harmonized_value` via the
  static bbox lookup table, and never falls back to UNKNOWN(4) solely because of a
  `ServiceExceptionReport` or a layer-name mismatch.
- **Preservation**: Existing parsing/processing behavior for every canton other than ZH (GML
  `featureMember` extraction, MapServer `*_feature` extraction, `property_values` / layer-name
  matching, and transport-level `geoservice_unavailable` handling), which must remain byte-for-byte
  identical.
- **`waermenutzung-zonen`**: The single real, queryable WMS layer on the ZH server that covers
  groundwater heat-use Zones A–F. Its `GetFeatureInfo` response carries only a bounding box, no
  attributes.
- **`erdwaermesonden-auflagen`**: The WMS layer representing borehole-heat-exchanger restrictions.
  Marked `queryable="0"` on the server; `GetFeatureInfo` against it is always rejected.
- **`bbox_zones`**: A new, ZH-only `Layer` config field — a static list mapping an observed
  `gml:Box` bounding box to a zone's `target_harmonized_value` / `desc`, used instead of
  `property_values` when the geoservice returns no attributes.
- **`queryable`**: A new, generic `Layer` config field (default `true`) marking whether a layer should
  be included in the WMS `QUERY_LAYERS` parameter. When `false`, the layer stays in `LAYERS` (so the
  request shape still matches what the server expects) but is never asked to resolve a feature.

## Bug Details

### Bug Condition

The bug manifests for every request whose coordinate resolves to canton ZH, because the layer list
`fetch_features_for_point` builds from `ZH.yaml` always includes layer names that are either
non-existent (`waermenutzung-zone-a`..`-f`) or non-queryable (`erdwaermesonden-auflagen`). The server
replies HTTP 200 with a `ServiceExceptionReport` (`LayerNotDefined`), which `httpx`'s
`raise_for_status()` does not catch. `parse_wms_getfeatureinfo` then finds no `gml:featureMember` /
`*_feature` elements, falls through to the ZH special case, finds no `gml:name` element either (the
real `waermenutzung-zonen` layer's response has no such attribute), and returns an empty feature list,
so `process_ground_category` falls back to `harmonized_value=4`.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type (coord_x: float, coord_y: float)
  OUTPUT: boolean

  canton := resolveCanton(input.coord_x, input.coord_y)   // via geo.admin.ch
  RETURN canton == "ZH"
         // Under the current (unfixed) ZH.yaml, this condition is sufficient:
         // every ZH coordinate hits the stale/non-queryable layer list below.
END FUNCTION
```

### Examples

- `fetch_features_for_point` for the Zone A ground control point (2688561, 1274977) sends
  `QUERY_LAYERS=erdwaermesonden-auflagen,waermenutzung-zone-a,...,waermenutzung-zone-f`. The server
  returns a `ServiceExceptionReport` (`LayerNotDefined`) with HTTP 200. Expected: `harmonized_value=3`.
  Actual: `harmonized_value=4`, empty `source_values`.
- Even replacing the layer list with just `waermenutzung-zonen`, `GetFeatureInfo` for the same point
  returns `<gml:boundedBy><gml:Box>...</gml:Box></gml:boundedBy>` with no `gml:name` and no other
  attribute. The current ZH special case (`root.find(".//gml:name", ns)`) finds nothing and still
  returns an empty feature list.
- Querying `erdwaermesonden-auflagen` alone (to check the heat-exchanger restriction for ground control
  point 1, which combines "Auflagen & waermenutzung-zone-d") is rejected by the server independently of
  the above, because the layer is `queryable="0"`.
- Edge case: a coordinate that resolves to ZH but falls outside every mapped zone bbox should still
  resolve to UNKNOWN(4) — that is correct behavior, not a bug, and must be preserved by the fix.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `parse_wms_getfeatureinfo`'s `gml:featureMember` extraction (used by other GML cantons) must continue
  to work exactly as before.
- `parse_wms_getfeatureinfo`'s MapServer `*_feature` extraction must continue to work exactly as
  before.
- `process_ground_category`'s `property_values` matching and layer-presence (`target_harmonized_value`
  without `property_values`) matching must continue to work exactly as before for every layer that does
  not define `bbox_zones`.
- WMS/ESRI transport-level failures (timeout, 4xx/5xx, connection error) must continue to return
  `geoservice_unavailable` exactly as before, for every canton including ZH.
- The `QUERY_LAYERS`/`LAYERS` construction must continue to produce an identical, comma-joined list of
  *all* configured layer names for every canton whose layers don't opt out via the new `queryable: false`
  field (i.e. every canton other than ZH is unaffected, since `queryable` defaults to `true`).

**Scope:**
All requests that do NOT resolve to canton ZH are completely unaffected by this fix. This includes:
- Every other active canton's WMS GML/MapServer responses.
- Every ESRI REST (`arcgis/json`) canton (GE, FR).
- Requests that fail at the HTTP transport level, for any canton.

## Hypothesized Root Cause

Confirmed via live investigation (see Overview):

1. **Stale per-zone layer names**: `ZH.yaml` references six layer names
   (`waermenutzung-zone-a`..`-f`) that were presumably valid at some point but no longer exist on the
   server; the server only publishes the combined `waermenutzung-zonen` layer.

2. **Non-queryable layer queried anyway**: `erdwaermesonden-auflagen` is configured with
   `property_values` as if `GetFeatureInfo` against it worked, but `GetCapabilities` marks it
   `queryable="0"` and the server rejects any query against it.

3. **No attribute payload to match against**: Even the real `waermenutzung-zonen` layer's
   `GetFeatureInfo` response carries no attribute (no `gml:name`, no zone label) — only a bounding box.
   The existing `property_values`/`gml:name` matching strategy cannot work against this layer under any
   layer-name fix, because there is no string to match.

4. **Silent `ServiceExceptionReport` swallowing**: HTTP 200 + `ServiceExceptionReport` is not treated as
   a transport error by `httpx.raise_for_status()`, so the undefined-layer condition surfaces only as an
   empty feature list deep in the parser, making the root cause non-obvious from the API response alone.

## Correctness Properties

Property 1: Bug Condition - ZH zone resolution via bounding-box lookup

_For any_ input where the bug condition holds (the coordinate resolves to canton ZH), the fixed system
SHALL send a `GetFeatureInfo` request whose `QUERY_LAYERS` contains only `waermenutzung-zonen` (the
real, queryable layer), SHALL NOT receive a `ServiceExceptionReport` caused by an undefined layer name,
and, when the returned bounding box matches an entry in the static `bbox_zones` lookup table, SHALL
resolve `harmonized_value` to that entry's `target_harmonized_value` instead of falling back to
UNKNOWN(4).

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - non-ZH parsing and processing behavior

_For any_ input where the bug condition does NOT hold (the coordinate resolves to a canton other than
ZH, or the request fails at the HTTP transport level), the fixed code SHALL produce exactly the same
result as the original code: `parse_wms_getfeatureinfo`'s `gml:featureMember` / `*_feature` extraction
is unchanged, `process_ground_category`'s `property_values` / layer-presence matching is unchanged for
every layer without `bbox_zones`, and transport-level failures continue to yield
`geoservice_unavailable`.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

**Known, documented exclusion from scope (not covered by either property):** because
`erdwaermesonden-auflagen` cannot be queried under any configuration found during investigation, the
"Auflagen für Erdwärmesonden" restriction itself is not detectable by this fix. Ground control point 1
(`2677790, 1260185`, labelled "Auflagen & waermenutzung-zone-d", currently expected `3`) will resolve to
Zone D's bbox-matched value (`2`) after this fix, not `3`, since only the zone layer contributes a
result. This is a real gap in requirement 2.3 as literally written and is called out explicitly in Fix
Implementation below rather than silently "fixed" — it should be confirmed with the user before task
execution (e.g. by updating that control point's expected value to `2`, or by scoping a follow-up
bugfix for the Auflagen restriction specifically).

## Fix Implementation

### Changes Required

**File**: `src/drillapi/cantons_configuration/schema.py`

1. **Add `queryable` field to `Layer`** (generic, default-safe):
   ```python
   # Whether this layer should be included in WMS QUERY_LAYERS. Defaults to True
   # so every existing canton is unaffected. Set False for a layer that exists
   # only in LAYERS (e.g. ZH's erdwaermesonden-auflagen, which the server marks
   # queryable="0" and rejects outright if placed in QUERY_LAYERS).
   queryable: bool = True
   ```

2. **Add `BboxZone` model and `bbox_zones` field on `Layer`** (ZH-only, additive):
   ```python
   class BboxZone(BaseModel):
       """A static bounding box observed for one WMS zone feature, used to
       resolve zone identity when GetFeatureInfo returns no attributes
       (ZH's `waermenutzung-zonen` layer)."""

       model_config = ConfigDict(extra="forbid")

       bbox: Annotated[list[float], Field(min_length=4, max_length=4)]
       name: str
       target_harmonized_value: GroundSuitability
       desc: str | None = None
   ```
   ```python
   # ZH-only: static bbox->zone lookup used instead of property_values when the
   # geoservice's GetFeatureInfo response carries no attribute payload.
   bbox_zones: list[BboxZone] | None = None
   ```

**File**: `src/drillapi/cantons_configuration/data/ZH.yaml`

3. **Replace the seven-layer list with two layers**:
   - `erdwaermesonden-auflagen`: keep `property_values` as-is (unused until/unless a working query path
     is found), add `queryable: false`.
   - `waermenutzung-zonen` (renamed from the six stale `waermenutzung-zone-*` entries): drop
     `property_values`/`property_name`'s attribute-matching role for this layer and add `bbox_zones`
     with one entry per zone (A–F). Each entry's `bbox` is the live `gml:Box` coordinates observed for
     that zone's documented `ground_control_point` (recorded once during implementation, e.g. the boxes
     already observed for Zones A/B/C during investigation, plus D/E/F queried the same way); `name` /
     `target_harmonized_value` / `desc` carry over unchanged from today's per-zone layer entries.
   - `property_name` stays `name` for both layers for schema consistency, even though
     `waermenutzung-zonen` no longer matches on it directly (it's matched via `bbox_zones` instead).

**File**: `src/drillapi/services/processing.py`

4. **`fetch_features_for_point` (WMS branch)**: build two comma-joined lists instead of one —
   `layers_list` (all layer names, used for `LAYERS`) and `query_layers_list` (only layers where
   `layer.get("queryable", True)` is `True`, used for `QUERY_LAYERS`). Non-ZH cantons have no
   `queryable: false` entries, so `query_layers_list == layers_list` for them — zero behavior change.

5. **`parse_wms_getfeatureinfo` ZH special case**: replace the `gml:name` lookup with a bounding-box
   extraction, still gated on `config["name"] == "ZH"` so no other canton is touched:
   ```python
   # ZH geoservice is a special and unique case: its only queryable layer
   # (waermenutzung-zonen) returns no attributes, only a bounding box
   # (gml:boundedBy/gml:Box) identifying which zone feature was hit.
   if not features and config["name"] == "ZH":
       box_elem = root.find(".//gml:boundedBy/gml:Box", ns)
       if box_elem is not None:
           coords = _parse_gml_box(box_elem, ns)  # -> [minx, miny, maxx, maxy] | None
           if coords is not None:
               features.append({"bbox": coords})
   ```
   Add a small `_parse_gml_box` helper that reads the two `gml:coordinates` (or `gml:coord`/`gml:pos`
   pairs, depending on GML version) inside the `gml:Box` and returns a 4-element float list, returning
   `None` on any malformed input (so parsing failures degrade to "no feature", not a crash).

6. **`process_ground_category`**: add a `bbox_zones`-matching branch, evaluated before the existing
   `property_values` branch, so it is purely additive for layers that don't define `bbox_zones`:
   ```python
   bbox_zones = layer_cfg.get("bbox_zones")
   if bbox_zones:
       for feature in ground_features:
           feature_bbox = feature.get("bbox") if isinstance(feature, dict) else None
           if feature_bbox is None:
               continue
           for zone in bbox_zones:
               if _bbox_matches(feature_bbox, zone["bbox"]):
                   mapped_values.append(zone.get("target_harmonized_value"))
                   source_values.append(zone.get("desc"))
                   break
   elif property_values:
       ...  # existing logic, unchanged
   else:
       ...  # existing layer-presence logic, unchanged
   ```
   Add a `_bbox_matches(a, b, tolerance=0.5)` helper comparing all four coordinates with
   `math.isclose`/absolute tolerance (meters, EPSG:2056), since the server returns the same feature's
   box deterministically but exact binary float equality shouldn't be relied on.

7. **Existing ZH unit tests** `test_parse_zh_special_case` / `test_parse_zh_no_name_element` in
   `tests/test_processing.py` encode the old `gml:name`-based special case and must be rewritten to
   assert the new bbox-based extraction. This is an intentional replacement of ZH-only test behavior,
   not a regression under requirements 3.1–3.4 (those requirements cover non-ZH canton logic and
   transport-level failures only).

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the
bug on unfixed code (to confirm the layer-name/queryability/no-attribute root cause), then verify the
fix resolves the correct zone for ZH and leaves every other canton's behavior byte-for-byte unchanged.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix, confirming the
three root causes (stale layer names, non-queryable layer, attribute-less response).

**Test Plan**: Replay `fetch_features_for_point` against a recorded (fixture) `ServiceExceptionReport`
body for the stale layer list, and against a recorded attribute-less `waermenutzung-zonen` GML response,
on the CURRENT/unfixed code.

**Test Cases**:
1. **Stale layer list test**: Feed a recorded `ServiceExceptionReport` (`LayerNotDefined`) body through
   `parse_wms_getfeatureinfo` with `config={"name": "ZH"}` and assert it returns `[]` (will pass on
   unfixed code — this *is* the bug, confirming the fallthrough).
2. **Attribute-less zone response test**: Feed a recorded `waermenutzung-zonen` GML response
   (`gml:boundedBy`/`gml:Box`, no `gml:name`) through the unfixed `parse_wms_getfeatureinfo` and assert
   it returns `[]` (confirms the current `gml:name` special case cannot recover zone identity even with
   the correct layer name).
3. **Non-queryable layer test**: Feed a recorded `erdwaermesonden-auflagen`-only
   `ServiceExceptionReport` through the unfixed pipeline and assert the fallback to `harmonized_value=4`
   (confirms this layer independently fails regardless of the zone-layer fix).

**Expected Counterexamples**:
- All three cases return empty features / UNKNOWN(4) on unfixed code, confirming the root cause
  analysis rather than refuting it.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function resolves the
correct zone.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fetch_and_process_fixed(input)
  ASSERT expectedBehavior(result)
END FOR

FUNCTION expectedBehavior(result)
  // No ServiceExceptionReport-driven empty-feature fallback, and the zone's
  // configured target_harmonized_value is reached when the point falls
  // inside a mapped zone bbox.
  RETURN result.query_layers == ["waermenutzung-zonen"]
         AND (result.harmonized_value != UNKNOWN
              OR pointOutsideAllKnownZoneBboxes(input))
END FUNCTION
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces
the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT original_parse_and_process(input) = fixed_parse_and_process(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many random GML/MapServer/ESRI response shapes automatically, across cantons.
- It catches edge cases (missing fields, unusual nesting) that manual unit tests might miss.
- It provides strong guarantees that `queryable` defaulting to `True` and the new `bbox_zones` branch
  being `None`-guarded never alter behavior for any non-ZH layer config.

**Test Plan**: Observe current behavior on unfixed code for `gml:featureMember`, `*_feature`, and
`property_values`/layer-presence matching across existing non-ZH fixtures, then write tests asserting
the fixed code produces identical output.

**Test Cases**:
1. **GML `featureMember` preservation**: Verify a non-ZH GML response with `gml:featureMember` elements
   parses identically before and after the fix.
2. **MapServer `*_feature` preservation**: Verify a `msGMLOutput` response parses identically before and
   after the fix.
3. **`property_values` matching preservation**: Verify `process_ground_category` for a canton with
   `property_values` (no `bbox_zones`) produces identical `harmonized_value`/`source_values` before and
   after the fix.
4. **`QUERY_LAYERS`/`LAYERS` construction preservation**: Verify that for every canton other than ZH
   (none of which set `queryable: false`), the built `QUERY_LAYERS` string is identical to the current
   `LAYERS` string.
5. **Transport failure preservation**: Verify timeout/4xx/5xx/connection-error handling still returns
   `geoservice_unavailable` for ZH and non-ZH cantons alike.

### Unit Tests

- `parse_wms_getfeatureinfo` with a `ServiceExceptionReport` body and `config={"name": "ZH"}` — asserts
  no crash and an empty feature list (not a regression target, but a documented, still-possible failure
  mode if the server ever changes again).
- `parse_wms_getfeatureinfo` with a `gml:boundedBy`/`gml:Box` response and `config={"name": "ZH"}` —
  asserts a single feature with the extracted `bbox` list.
- `parse_wms_getfeatureinfo` ZH case with a malformed/missing `gml:Box` — asserts an empty feature list
  (no crash).
- `process_ground_category` with a `bbox_zones`-configured layer and a matching feature bbox — asserts
  the correct `target_harmonized_value`/`desc` is selected.
- `process_ground_category` with a `bbox_zones`-configured layer and a feature bbox that matches no
  known zone — asserts fallback to UNKNOWN(4).
- `fetch_features_for_point` WMS branch with a mix of `queryable: true`/`false` layers — asserts
  `QUERY_LAYERS` excludes the `false` ones while `LAYERS` includes all of them.

### Property-Based Tests

- Generate random bbox pairs within/outside a small tolerance and verify `_bbox_matches` behaves
  correctly at the tolerance boundary (true inside, false outside).
- Generate random `Layer` configs with/without `queryable`/`bbox_zones` set and verify
  `process_ground_category`/`fetch_features_for_point` behavior for every non-ZH-shaped config (no
  `bbox_zones`, `queryable` absent or `true`) is byte-identical to the pre-fix implementation.
- Generate random GML fixtures with `gml:featureMember` elements and verify extraction is unaffected by
  the new ZH-only bbox branch (which only runs when `features` is still empty after the existing
  extraction steps).

### Integration Tests

- Replay `fetch_features_for_point` against recorded live responses for all documented ZH
  `ground_control_point` entries (Zones A–E, plus the Auflagen/Zone D combination point) and assert the
  resulting `harmonized_value` matches each entry's expected value, with the documented exception for
  the Auflagen-only contribution noted in Correctness Properties.
- Full `/v1/drill-category/{coord_x}/{coord_y}` route test for a ZH coordinate — asserts a non-UNKNOWN
  `harmonized_value` and a populated `layer_results` entry for `waermenutzung-zonen`.
- Full route test for a representative non-ZH canton coordinate (e.g. an existing GE/FR/BE fixture) —
  asserts the response is unchanged from the current baseline.
