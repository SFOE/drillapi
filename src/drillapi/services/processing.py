import json
import logging
import math
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

        # WMS GetFeatureInfo
        else:
            delta = config["bbox_delta"]
            width = 101
            height = 101

            minx, miny = coord_x - delta, coord_y - delta
            maxx, maxy = coord_x + delta, coord_y + delta
            bbox = f"{minx},{miny},{maxx},{maxy}"

            layers_list = ",".join([layer["name"] for layer in config["layers"]])
            query_layers_list = ",".join(
                [
                    layer["name"]
                    for layer in config["layers"]
                    if layer.get("queryable", True)
                ]
            )

            i = int((coord_x - minx) / (maxx - minx) * width)
            j = int((maxy - coord_y) / (maxy - miny) * height)

            params_wms = {
                "SERVICE": "WMS",
                "VERSION": "1.3.0",
                "REQUEST": "GetFeatureInfo",
                "QUERY_LAYERS": query_layers_list,
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

        # ZH geoservice is a special and unique case: its only queryable layer
        # (waermenutzung-zonen) returns no attributes, only a bounding box
        # (gml:boundedBy/gml:Box) identifying which zone feature was hit.
        if not features and config["name"] == "ZH":
            box_elem = root.find(".//gml:boundedBy/gml:Box", ns)
            if box_elem is not None:
                coords = _parse_gml_box(box_elem, ns)
                if coords is not None:
                    features.append({"bbox": coords})
        return features


def _parse_gml_box(box_elem, ns: dict) -> list[float] | None:
    """
    Extract [minx, miny, maxx, maxy] from a <gml:Box> element.

    Supports both the GML2-style single <gml:coordinates> element (holding
    two "x,y" pairs separated by whitespace) and the GML3-style pair of
    <gml:coord>/<gml:pos> elements (each holding its own x/y). Returns None
    on any malformed or missing input instead of raising, so parsing
    failures degrade to "no feature" rather than a crash.
    """
    try:
        coordinates_elem = box_elem.find("gml:coordinates", ns)
        if coordinates_elem is not None and coordinates_elem.text:
            raw = coordinates_elem.text.strip()
            pairs = raw.split()
            if len(pairs) != 2:
                return None
            minx, miny = (float(v) for v in pairs[0].split(","))
            maxx, maxy = (float(v) for v in pairs[1].split(","))
            return [minx, miny, maxx, maxy]

        # GML3-style: two <gml:coord> elements, each with <gml:X>/<gml:Y>,
        # or two <gml:pos> elements holding "x y" text directly.
        coord_elems = box_elem.findall("gml:coord", ns)
        if len(coord_elems) == 2:
            points = []
            for coord_elem in coord_elems:
                x_elem = coord_elem.find("gml:X", ns)
                y_elem = coord_elem.find("gml:Y", ns)
                if (
                    x_elem is None
                    or y_elem is None
                    or not x_elem.text
                    or not y_elem.text
                ):
                    return None
                points.append((float(x_elem.text.strip()), float(y_elem.text.strip())))
            (minx, miny), (maxx, maxy) = points
            return [minx, miny, maxx, maxy]

        pos_elems = box_elem.findall("gml:pos", ns)
        if len(pos_elems) == 2:
            points = []
            for pos_elem in pos_elems:
                if not pos_elem.text:
                    return None
                values = pos_elem.text.strip().split()
                if len(values) != 2:
                    return None
                points.append((float(values[0]), float(values[1])))
            (minx, miny), (maxx, maxy) = points
            return [minx, miny, maxx, maxy]

        return None
    except ValueError, TypeError, AttributeError, IndexError:
        return None


def _bbox_matches(a: list[float], b: list[float], tolerance: float = 0.5) -> bool:
    """
    Compare two [minx, miny, maxx, maxy] bounding boxes for equality within
    an absolute tolerance (meters, EPSG:2056). A small tolerance accounts for
    floating point noise introduced by GML parsing rather than requiring
    exact binary float equality.
    """
    if a is None or b is None or len(a) != 4 or len(b) != 4:
        return False
    return all(math.isclose(a[i], b[i], abs_tol=tolerance) for i in range(4))


def process_ground_category(
    ground_features: list,
    config_layers: list,
):
    """
    Reclass canton response into normalized values.
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
        bbox_zones = layer_cfg.get("bbox_zones")

        property_name_value = None

        # ZH-only, additive: layers with no attribute payload (only a
        # gml:boundedBy/gml:Box bounding box per feature) resolve zone
        # identity via a static bbox->zone lookup table instead of matching
        # on an attribute value. Evaluated before property_values so it
        # never interferes with the existing matching logic for layers that
        # don't define bbox_zones.
        if bbox_zones:
            matched_zone_name = None
            for feature in ground_features:
                feature_bbox = (
                    feature.get("bbox") if isinstance(feature, dict) else None
                )
                if feature_bbox is None:
                    continue
                for zone in bbox_zones:
                    if _bbox_matches(feature_bbox, zone.get("bbox")):
                        mapped_values.append(zone.get("target_harmonized_value"))
                        source_values.append(zone.get("desc"))
                        matched_zone_name = zone.get("name")
                        break

            # bbox-matched features have no property_name_value (there's no
            # attribute payload to read), so layer_results bookkeeping below
            # would otherwise never fire for this layer. Record the matched
            # zone's name instead so a bbox-resolved layer still shows up in
            # layer_results for debugging, mirroring the non-bbox branch.
            if matched_zone_name:
                layer_results.append(
                    {
                        "layer": layer_name,
                        "property_name": property_name,
                        "value": matched_zone_name,
                    }
                )

        else:
            for feature in ground_features:
                # ESRI REST support
                if isinstance(feature, dict):
                    if "attributes" in feature and isinstance(
                        feature["attributes"], dict
                    ):
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

                # For some cantons, only the presence or absence of feature is used to define suitability
                else:
                    if layer_cfg.get("property_name") == feature.get("layerName"):
                        mapped_values.append(layer_cfg.get("target_harmonized_value"))

        # Helping dict useful to identify issues. Only "harmonized_value" is useful for frontend application
        if property_name_value:
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

    # If no value is found, fallback value is = 4
    if not harmonized_value:
        harmonized_value = 4

    source_values_str = ""
    if source_values:
        source_values_str = ",".join(str(v) for v in source_values if v is not None)

    return GroundCategory(
        layer_results=layer_results,
        harmonized_value=harmonized_value,
        source_values=source_values_str,
    )
