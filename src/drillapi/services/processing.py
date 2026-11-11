import json
import logging
import re
import xml.etree.ElementTree as ET

import httpx
from fastapi import HTTPException
from owslib.etree import etree

from ..models.models import GroundCategory

logger = logging.getLogger(__name__)


# STRING NORMALIZATION
def normalize_string(value: str) -> str:
    """
    Fix common double-encoding issues from WMS or ESRI JSON responses.
    Example: 'unzul\\u00e4ssig' → 'unzulässig'
    """
    if not isinstance(value, str):
        return value
    try:
        # Try decoding strings that were double-encoded (latin1→utf8)
        return value.encode("latin1").decode("utf-8")
    except UnicodeDecodeError, UnicodeEncodeError:
        return value


# WFS RESPONSE INSPECTION
# Geometry / envelope tags that are never classification attributes.
_WFS_SKIP_TAGS = frozenset(
    {
        "boundedby",
        "geometry",
        "msgeometry",
        "geom",
        "polygon",
        "multipolygon",
        "multisurface",
        "surface",
        "envelope",
        "point",
        "linestring",
        "shape",
    }
)


def _wfs_response_has_feature(content: bytes) -> bool:
    """Return True if a WFS 2.0 GetFeature response contains >= 1 feature.

    Presence-based matching only needs to know whether a feature type
    intersects the queried point, not its attributes. A WFS 2.0
    ``FeatureCollection`` advertises ``numberReturned`` / ``numberMatched``;
    we fall back to counting ``member`` / ``featureMember`` elements when the
    count attribute is absent.

    Raises:
        ValueError: if the service returned an OWS/WFS exception report, so the
            caller can surface it as a geoservice error instead of silently
            treating it as "no feature found".
    """
    text = content.decode("utf-8", errors="ignore")

    if "ExceptionReport" in text or "ServiceException" in text:
        raise ValueError("WFS returned a service exception")

    # Fast path: the collection declares how many features it returned.
    match = re.search(r'numberReturned\s*=\s*"(\d+)"', text)
    if match:
        return int(match.group(1)) > 0

    # Fallback: any (feature)member element indicates at least one feature.
    return bool(re.search(r"<(?:\w+:)?(?:member|featureMember)\b", text))


def _parse_wfs_features(content: bytes) -> list[dict]:
    """Parse a WFS 2.0 GetFeature (GML) response into attribute dicts.

    Returns one dict per feature, keyed by the (namespace-stripped) attribute
    tag -> text value, skipping geometry/envelope elements. This supports both
    attribute-based matching (e.g. BL ``ov_kategor``, TG ``eignungszone``) and
    presence-based matching (a feature with no usable attributes still yields
    an empty-ish dict, so the caller can tag it with ``layerName``).

    Raises:
        ValueError: on an OWS/WFS exception report, so the caller surfaces it
            as a geoservice error rather than "no feature".
    """
    text = content.decode("utf-8", errors="ignore")

    if "ExceptionReport" in text or "ServiceException" in text:
        raise ValueError("WFS returned a service exception")

    try:
        root = etree.fromstring(text.encode("utf-8"))
    except etree.XMLSyntaxError, ValueError:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            raise HTTPException(500, f"Invalid WFS XML/GML: {e}")

    features: list[dict] = []
    # WFS 2.0 uses <wfs:member>; WFS 1.x uses <gml:featureMember>.
    members = [
        el
        for el in root.iter()
        if el.tag.split("}", 1)[-1] in ("member", "featureMember")
    ]
    for member in members:
        # The feature element is the member's single child (e.g. <ms:Layer>).
        children = list(member)
        if not children:
            continue
        feature_el = children[0]
        fdict: dict = {}
        for attr in feature_el.iter():
            tag = attr.tag.split("}", 1)[-1]
            if tag.lower() in _WFS_SKIP_TAGS:
                continue
            # Only leaf text nodes carry attribute values.
            if len(attr) == 0 and attr.text and attr.text.strip():
                fdict[tag] = attr.text.strip()
        features.append(fdict)

    return features


# CANTON LOOKUP (geo.admin.ch)
async def get_canton_from_coordinates(coord_x: float, coord_y: float):
    """
    Query geo.admin.ch to find the canton (AK code) for EPSG:2056 coordinates.
    Returns: list of dicts (geo.admin.ch "results" array)
    """

    url = "https://api3.geo.admin.ch/rest/services/ech/MapServer/identify"
    params = {
        "geometry": f"{coord_x},{coord_y}",
        "geometryType": "esriGeometryPoint",
        "sr": "2056",
        "layers": "all:ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
        "tolerance": "0",
        "lang": "en",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            results = payload.get("results", [])
    except httpx.RequestError as e:
        logger.error(
            "Network error fetching canton for (%.2f, %.2f): %s", coord_x, coord_y, e
        )
        results = []
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error %d for (%.2f, %.2f): %s",
            e.response.status_code,
            coord_x,
            coord_y,
            e,
        )
        results = []
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON for (%.2f, %.2f): %s", coord_x, coord_y, e)
        results = []

    return results


# FETCH WMS OR ESRI FEATURES
async def fetch_features_for_point(coord_x: float, coord_y: float, config: dict):
    """
    Fetch features for a coordinate using either:
      - ESRI REST Feature Service (info_format='arcgis/json'), or
      - WMS GetFeatureInfo for other formats.

    Returns:
        dict: {
            "features": [...],
            "full_url": str,
            "error": Optional[str]
        }
    """
    info_format = config["info_format"].lower()
    features = []
    full_url = ""
    error_message = None

    async with httpx.AsyncClient(timeout=20.0) as client:
        # ESRI REST
        if "arcgis" in info_format:
            for layer in config["layers"]:
                layer_id = layer.get("id")
                if layer_id is None:
                    raise RuntimeError(
                        "Layer config missing 'id' for ESRI REST service"
                    )

                esri_url = f"{config['query_url'].rstrip('/')}/{layer_id}/query"

                params = {
                    "geometry": f"{coord_x},{coord_y}",
                    "geometryType": "esriGeometryPoint",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "returnGeometry": "false",
                    "f": "json",
                }
                try:
                    resp = await client.get(esri_url, params=params)
                    full_url = str(resp.request.url)
                    resp.raise_for_status()

                    data = resp.json()
                    features = data.get("features") or []
                except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
                    error_message = f"WMS request failed: {e}"
                    logger.error("%s — URL: %s", error_message, full_url or esri_url)
                    return {
                        "features": [],
                        "full_url": full_url or esri_url,
                        "error": error_message,
                        "geoservice_unavailable": True,
                    }

        # WFS GetFeature
        #
        # Several cantons expose a WFS that is more reliable than the legacy
        # WMS GetFeatureInfo (and some, like ZH and BL, no longer answer
        # GetFeatureInfo at all). We query each configured layer with a small
        # bbox around the point and parse the returned features. Each feature is
        # tagged with ``layerName`` = the layer's configured ``name`` so that
        # ``process_ground_category`` can match either:
        #   - by attribute value (``property_values`` against the attribute
        #     named by ``property_name``, e.g. TG ``eignungszone``), or
        #   - by mere presence (no ``property_values``; the layer-level
        #     ``target_harmonized_value`` applies, e.g. BL Fall A).
        elif "wfs" in info_format:
            query_url = config["query_url"]
            urls = []
            for layer in config["layers"]:
                layer_name = layer["name"]
                # WFS feature types are namespaced (``ms:<layer>`` on MapServer).
                # `.get` may return an explicit None (schema default), so fall
                # back to `ms:<name>` whenever it is missing or empty.
                type_name = layer.get("wfs_type_name") or f"ms:{layer_name}"
                # Use a precise point INTERSECTS filter (not a bbox): a bbox
                # matches a feature by its bounding-box envelope, which wrongly
                # catches neighbouring or canton-wide polygons. The geometry
                # property name varies per server (MapServer uses "geom" or
                # "msGeometry"); it is overridable per layer.
                geom_prop = layer.get("geometry_property") or "geom"
                point_filter = (
                    '<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" '
                    'xmlns:gml="http://www.opengis.net/gml/3.2">'
                    "<fes:Intersects>"
                    f"<fes:ValueReference>{geom_prop}</fes:ValueReference>"
                    '<gml:Point srsName="urn:ogc:def:crs:EPSG::2056">'
                    f"<gml:pos>{coord_x} {coord_y}</gml:pos>"
                    "</gml:Point></fes:Intersects></fes:Filter>"
                )
                params_wfs = {
                    "SERVICE": "WFS",
                    "VERSION": "2.0.0",
                    "REQUEST": "GetFeature",
                    "TYPENAMES": type_name,
                    "SRSNAME": "EPSG:2056",
                    "COUNT": config.get("feature_count", 10),
                    "FILTER": point_filter,
                }
                this_url = query_url
                try:
                    resp = await client.get(query_url, params=params_wfs)
                    this_url = str(resp.request.url)
                    urls.append(this_url)
                    resp.raise_for_status()
                except (httpx.HTTPError, httpx.StreamError) as e:
                    error_message = f"WFS request failed: {e}"
                    logger.error("%s — URL: %s", error_message, this_url or query_url)
                    return {
                        "features": [],
                        "full_url": this_url or query_url,
                        "error": error_message,
                        "geoservice_unavailable": True,
                    }

                try:
                    for feature in _parse_wfs_features(resp.content):
                        feature["layerName"] = layer_name
                        features.append(feature)
                except HTTPException:
                    raise
                except (ValueError, TypeError) as e:
                    error_message = f"Failed to parse WFS response: {e}"
                    logger.error("%s — URL: %s", error_message, this_url)
                    return {
                        "features": [],
                        "full_url": this_url,
                        "error": error_message,
                        "geoservice_unavailable": True,
                    }

            return {
                "features": features,
                "full_url": "\n".join(urls),
                "error": error_message,
            }

        # WMS GetFeatureInfo
        else:
            delta = config["bbox_delta"]
            width = 101
            height = 101

            minx, miny = coord_x - delta, coord_y - delta
            maxx, maxy = coord_x + delta, coord_y + delta
            bbox = f"{minx},{miny},{maxx},{maxy}"

            layers_list = ",".join([layer["name"] for layer in config["layers"]])

            i = int((coord_x - minx) / (maxx - minx) * width)
            j = int((maxy - coord_y) / (maxy - miny) * height)

            params_wms = {
                "SERVICE": "WMS",
                "VERSION": "1.3.0",
                "REQUEST": "GetFeatureInfo",
                "QUERY_LAYERS": layers_list,
                "LAYERS": layers_list,
                "INFO_FORMAT": config.get("info_format", "text/plain"),
                "I": str(i),
                "J": str(j),
                "CRS": "EPSG:2056",
                "WIDTH": str(width),
                "HEIGHT": str(height),
                "BBOX": bbox,
                "STYLES": config.get("style", ""),
                "FEATURE_COUNT": config.get("feature_count", 10),
            }

            query_url = config["query_url"]
            try:
                resp = await client.get(query_url, params=params_wms)
                full_url = str(resp.request.url)
                resp.raise_for_status()
            except (httpx.HTTPError, httpx.StreamError) as e:
                error_message = f"WMS request failed: {e}"
                logger.error("%s — URL: %s", error_message, full_url or query_url)
                return {
                    "features": [],
                    "full_url": full_url or query_url,
                    "error": error_message,
                    "geoservice_unavailable": True,
                }

        try:
            features = parse_wms_getfeatureinfo(
                resp.content, config["info_format"], config
            )

            return {
                "features": features,
                "full_url": full_url,
                "error": error_message,
            }

        except HTTPException:
            # Re-raise genuine internal errors (e.g., invalid JSON/XML from parse_wms_getfeatureinfo)
            raise
        except (ValueError, TypeError, KeyError) as e:
            error_message = f"Failed to parse WMS or ESRI REST response: {e}"
            logger.error("%s — URL: %s", error_message, full_url)
            return {
                "features": [],
                "full_url": full_url,
                "error": error_message,
                "geoservice_unavailable": True,
            }


# PARSE WMS or REST responses
def parse_wms_getfeatureinfo(content: bytes, info_format: str, config: dict):
    """
    Parser for differents geoservices outputs
    """

    text = content.decode("utf-8", errors="ignore")
    info_format = (info_format or "").lower().strip()

    # JSON / ESRI REST / GEOJSON PARSING
    if "json" in info_format or "arcgis" in info_format:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(500, f"Invalid JSON: {e}")

        features = []
        # GeoJSON FeatureCollection
        if isinstance(data, dict) and data.get("type") == "FeatureCollection":
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                props["layerName"] = feature.get("layerName")
                if isinstance(props, dict):
                    features.append(props)

        #  ESRI REST JSON
        elif isinstance(data, dict) and "features" in data:
            for feature in data["features"]:
                # ESRI features usually have an "attributes" dict
                attrs = feature.get("attributes", {})
                # optionally add layerName if needed
                attrs["layerName"] = feature.get("layerName")
                features.append(attrs)

        return features

    else:
        # GML / XML PARSING  (OWSLib-compatible)
        try:
            root = etree.fromstring(text.encode("utf-8"))
        except etree.XMLSyntaxError, ValueError:
            try:
                root = ET.fromstring(text)
            except ET.ParseError as e:
                raise HTTPException(500, f"Invalid XML/GML: {e}")

        features = []
        ns = {"gml": "http://www.opengis.net/gml"}

        # 1) Standard GML <gml:featureMember>
        for fm in root.findall(".//gml:featureMember", ns):
            fdict = {}
            for el in fm.iter():
                tag = el.tag.split("}", 1)[-1]
                if tag.lower() in ("boundedby", "geometry", "polygon", "multipolygon"):
                    continue
                if el.text and el.text.strip():
                    fdict[tag] = el.text.strip()
            if fdict:
                features.append(fdict)

        # 2) MapServer msGMLOutput   <*_feature>

        for elem in root.iter():
            if re.search(r"_feature$", elem.tag):
                fdict = {}
                for child in elem:
                    tag = child.tag.split("}", 1)[-1]
                    if tag.lower() in ("boundedby", "geometry"):
                        continue
                    val = child.text.strip() if child.text else None
                    if val:
                        fdict[tag] = val
                if fdict:
                    features.append(fdict)

        # ZH geoservice is a special and unique case
        # It only returns a GML without atttibute but containing the layer that was found at location
        if not features and config["name"] == "ZH":
            name_elem = root.find(".//gml:name", ns)
            if name_elem is not None and name_elem.text and name_elem.text.strip():
                fdict = {"name": name_elem.text.strip()}
                features.append(fdict)
        return features


def process_ground_category(
    ground_features: list,
    config_layers: list,
    default_harmonized_value: int = 4,
):
    """
    Reclass canton response into normalized values.

    ``default_harmonized_value`` is returned when no configured layer matches.
    It defaults to 4 (UNKNOWN). Some cantons represent a category as the
    *absence* of a feature — e.g. BL encodes Fall A (unzulässig, 3) as a hole in
    the ``ohne_a`` layer — and set this to that category instead.
    """

    layer_results = []

    mapped_values = []
    source_values = []
    harmonized_value = None

    # For each canton, multiple layers are requested (single request to WMS / ESRI)
    # The returned feature(s) are then compared with mapping values defined for:
    #  - Each layer
    #  - Each possible value in each layer
    #  - Some geoservices associate one layer to one category. In this case, layer names are compared, not attribute values
    for layer_cfg in config_layers:
        layer_name = layer_cfg.get("name")
        property_name = layer_cfg.get("property_name")
        property_values = layer_cfg.get("property_values")

        property_name_value = None

        for feature in ground_features:
            # ESRI REST support
            if isinstance(feature, dict):
                if "attributes" in feature and isinstance(feature["attributes"], dict):
                    property_name_value = feature["attributes"].get(property_name)
                else:
                    property_name_value = feature.get(property_name)
            else:
                property_name_value = feature

            property_name_value = normalize_string(property_name_value)
            if property_values:
                for item in property_values:
                    # Match with values for layers that have a defined mapping
                    if item.get("name") == property_name_value:
                        mapped_values.append(item.get("target_harmonized_value"))
                        source_values.append(item.get("desc"))

            # For some cantons (ZH WFS), only the presence or absence of a
            # feature defines suitability: the feature carries no attribute, so
            # we match the layer by its tagged `layerName` instead of a value.
            else:
                if layer_cfg.get("property_name") == feature.get("layerName"):
                    mapped_values.append(layer_cfg.get("target_harmonized_value"))
                    desc = layer_cfg.get("desc")
                    source_values.append(desc)
                    layer_results.append(
                        {
                            "layer": layer_name,
                            "property_name": property_name,
                            "value": desc or layer_name,
                        }
                    )

        # Helping dict useful to identify issues. Only "harmonized_value" is useful for frontend application
        if property_values and property_name_value:
            layer_results.append(
                {
                    "layer": layer_name,
                    "property_name": property_name,
                    "value": property_name_value,
                }
            )

    # property_values variable contains the mapping between attribute value and drillapi categories (1,2,3)
    if mapped_values:
        harmonized_value = max(mapped_values)

    # If no value is found, use the canton's configured default (4 = UNKNOWN
    # unless the canton encodes a category as feature-absence, e.g. BL -> 3).
    if not harmonized_value:
        harmonized_value = default_harmonized_value

    source_values_str = ""
    if source_values:
        source_values_str = ",".join(str(v) for v in source_values if v is not None)

    return GroundCategory(
        layer_results=layer_results,
        harmonized_value=harmonized_value,
        source_values=source_values_str,
    )
