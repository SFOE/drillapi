# Bugfix Requirements Document

## Introduction

The geoservice integration for canton ZH (Zurich) never returns a correct drill-category value. Every ground control point defined in `src/drillapi/cantons_configuration/data/ZH.yaml` resolves to `harmonized_value=4` (UNKNOWN) instead of its documented expected value, as confirmed via the `/checker/ZH` route and by replaying `processing.fetch_features_for_point()` directly against the live ZH endpoint for all 5 `ground_control_point` entries.

Root cause hypothesis, based on direct inspection of the live WMS `GetCapabilities` response at `https://wms.zh.ch/AwelGSWaermewwwZHWMS`:

- `ZH.yaml` configures seven layers to be queried together (`erdwaermesonden-auflagen`, `waermenutzung-zone-a` through `waermenutzung-zone-f`), but the six per-zone layer names (`waermenutzung-zone-a`..`-f`) do not exist on the server. The server only publishes a single combined, queryable layer named `waermenutzung-zonen`.
- Because the combined `GetFeatureInfo` request references layer names the server doesn't recognize, the server responds with HTTP 200 and a `ServiceExceptionReport` body (`LayerNotDefined`). `httpx`'s `raise_for_status()` does not catch this, since the HTTP status is 200.
- `parse_wms_getfeatureinfo` cannot find `gml:featureMember` or `*_feature` elements in that exception body, falls through to the ZH-specific `<gml:name>` lookup, finds nothing there either, and returns an empty feature list.
- Separately, `erdwaermesonden-auflagen` is configured as if it were queryable, but `GetCapabilities` marks it `queryable="0"`, so a `GetFeatureInfo` request against it is rejected by the server independently of the layer-name issue above.
- Even if the real layer name `waermenutzung-zonen` were used instead of the stale per-zone names, its `GetFeatureInfo` response was found to contain only a bounding box per feature and a generic layer title in `<gml:name>` ("Wärmenutzungs Zonen") — not the zone-specific description strings (e.g. "Zone A (Schutzzonen und Schutzareale)") that `ZH.yaml`'s `property_values` are keyed on. This means a layer-name fix alone may not be sufficient to resolve the correct zone.

Open question for the design phase: does ZH publish an alternative endpoint (WFS, ArcGIS REST/FeatureServer, or a set of real per-zone layers with queryable attributes) that exposes zone-level and `erdwaermesonden-auflagen` data with usable attributes? The current WMS `waermenutzung-zonen` layer's `GetFeatureInfo` output carries no attribute payload that the existing WMS-scraping approach (including the ZH special case in `parse_wms_getfeatureinfo`) could use to distinguish zones.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the API queries ZH for any coordinate using the combined layer list from `ZH.yaml` (`erdwaermesonden-auflagen`, `waermenutzung-zone-a` through `waermenutzung-zone-f`) THEN the system sends a `GetFeatureInfo` request containing layer names that do not exist on the ZH WMS server, and the server returns HTTP 200 with a `ServiceExceptionReport` (`LayerNotDefined`) instead of feature data.

1.2 WHEN `parse_wms_getfeatureinfo` receives a `ServiceExceptionReport` body for config `name == "ZH"` THEN the system finds no `gml:featureMember` or `*_feature` elements, falls through to the ZH-specific `<gml:name>` lookup, finds no matching element there either, and returns an empty `features` list.

1.3 WHEN `fetch_features_for_point` / `process_ground_category` is evaluated for any of the 5 `ground_control_point` entries in `ZH.yaml` THEN the system returns `harmonized_value=4` (UNKNOWN) with empty `source_values`/`mapped_values`, instead of the expected control values (3, 3, 2, 2, 2).

1.4 WHEN the API includes `erdwaermesonden-auflagen` in the combined `GetFeatureInfo` request THEN the server rejects querying that layer because it is marked `queryable="0"` in `GetCapabilities`, even though `ZH.yaml` configures it with `property_values` expecting a name match of "Auflagen für Erdwärmesonden".

### Expected Behavior (Correct)

2.1 WHEN the API queries ZH for any coordinate THEN the system SHALL only request layer names (or use an alternative data source) that actually exist and are queryable on the ZH service, so it does not receive a `ServiceExceptionReport` for undefined layers.

2.2 WHEN the ZH service returns feature data for the zone layer(s) actually queried THEN the system SHALL be able to resolve which specific zone (A through F) was hit at the queried coordinate and map it to the correct `target_harmonized_value` defined in `ZH.yaml`.

2.3 WHEN all 5 documented `ground_control_point` entries in `ZH.yaml` are evaluated THEN the system SHALL return `harmonized_value` matching each entry's expected control value (3, 3, 2, 2, 2 respectively) with non-empty `source_values`/`mapped_values` where a match is expected.

2.4 WHEN the `erdwaermesonden-auflagen` restriction needs to be checked for a coordinate THEN the system SHALL use a request method and/or layer reference that the ZH service actually permits, instead of silently failing because the layer is not queryable via WMS `GetFeatureInfo`.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `parse_wms_getfeatureinfo` processes a valid GML response containing `gml:featureMember` elements for other cantons THEN the system SHALL CONTINUE TO extract feature attributes using the existing logic.

3.2 WHEN `parse_wms_getfeatureinfo` processes a MapServer `msGMLOutput` response containing `*_feature` elements for other cantons THEN the system SHALL CONTINUE TO extract feature attributes using the existing logic.

3.3 WHEN `process_ground_category` receives genuinely matched features for cantons other than ZH THEN the system SHALL CONTINUE TO compute `harmonized_value` using the existing `property_values` / layer-name matching logic unchanged.

3.4 WHEN a WMS or ESRI REST request fails at the HTTP transport level (timeout, 4xx/5xx status, connection error) THEN the system SHALL CONTINUE TO return `geoservice_unavailable` with an error message, as it does today.
