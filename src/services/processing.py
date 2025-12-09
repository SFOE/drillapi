import httpx
import json
import re
import xml.etree.ElementTree as ET
from fastapi import HTTPException
import logging
from owslib.etree import etree

logger = logging.getLogger(__name__)


# ============================================================
# STRING NORMALIZATION
# ============================================================
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
    except Exception:
        return value


# ============================================================
# CANTON LOOKUP (geo.admin.ch)
# ============================================================
def get_canton_from_coordinates(coord_x: float, coord_y: float):
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
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:
        logger.error("Failed to fetch canton for (%.2f, %.2f): %s", coord_x, coord_y, e)
        raise HTTPException(500, detail=f"Failed to fetch canton: {e}")

    results = payload.get("results", [])
    if not results:
        logger.warning(
            "No canton found for coordinates: (%.2f, %.2f)", coord_x, coord_y
        )
    return results


# ============================================================
# FETCH WMS OR ESRI FEATURES
# ============================================================
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
        try:
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

                    resp = await client.get(esri_url, params=params)
                    full_url = str(resp.request.url)
                    resp.raise_for_status()

                    data = resp.json()
                    features = data.get("features") or []

            # ---------- WMS GetFeatureInfo ----------
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
                except Exception as e:
                    error_message = f"WMS request failed: {e}"
                    logger.error("%s — URL: %s", error_message, full_url)
                    return {
                        "features": [],
                        "full_url": full_url,
                        "error": error_message,
                    }

                try:
                    features = await parse_wms_getfeatureinfo(
                        resp.content, config["info_format"], config
                    )
                except Exception as e:
                    error_message = f"Failed to parse WMS response: {e}"
                    logger.error("%s — URL: %s", error_message, full_url)

        except Exception as e:
            error_message = f"Unexpected error in fetch_features_for_point: {e}"
            logger.exception(error_message)
    # Always return structured result (even if empty)
    return {
        "features": features,
        "full_url": full_url,
        "error": error_message,
    }


# ============================================================
# PARSE WMS or REST responses
# ============================================================


async def parse_wms_getfeatureinfo(content: bytes, info_format: str, config: dict):
    """
    Parser for differents geoservices outputs
    """

    text = content.decode("utf-8", errors="ignore")
    info_format = (info_format or "").lower().strip()

    # ----------------------------------------------------------------------
    # JSON / ESRI REST / GEOJSON PARSING
    # ----------------------------------------------------------------------
    if "json" in info_format or "arcgis" in info_format:
        try:
            data = json.loads(text)
        except Exception as e:
            raise HTTPException(500, f"Invalid JSON: {e}")

        # -------------------------------
        # GeoJSON FeatureCollection
        # -------------------------------
        if isinstance(data, dict) and data.get("type") == "FeatureCollection":
            features = []

            for feature in data.get("features", []):
                props = feature.get("properties", {})
                props["layerName"] = feature.get("layerName")
                if isinstance(props, dict):
                    features.append(props)
            return features

    # ----------------------------------------------------------------------
    # GML / XML PARSING  (OWSLib-compatible)
    # ----------------------------------------------------------------------
    try:
        root = etree.fromstring(text.encode("utf-8"))
    except Exception:
        try:
            root = ET.fromstring(text)
        except Exception as e:
            raise HTTPException(500, f"Invalid XML/GML: {e}")

    features = []
    ns = {"gml": "http://www.opengis.net/gml"}

    # ----------------------------------------------------------------------
    # 1) Standard GML <gml:featureMember>
    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    # 2) MapServer msGMLOutput   <*_feature>
    # ----------------------------------------------------------------------

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
):
    """
    Reclass canton response into normalized values.
    """
    # -----------------------------------------------------------
    # No features → harmonized value = 4
    # -----------------------------------------------------------
    if not ground_features:
        return {
            "layer_results": [],
            "harmonized_value": 4,
        }

    layer_results = []

    mapped_values = []
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

        description = None

        for feature in ground_features:
            # ESRI REST support
            if isinstance(feature, dict):
                if "attributes" in feature and isinstance(feature["attributes"], dict):
                    value = feature["attributes"].get(property_name)
                else:
                    value = feature.get(property_name)
            else:
                value = feature

            value = normalize_string(value)
            if property_values:
                for item in property_values:
                    # Match with values for layers that have a defined mapping
                    if item.get("name") == value:
                        mapped_values.append(item.get("target_harmonized_value"))
                        description = item.get("desc")

            # For some cantons, only the presence or absence of feature is used to define suitability
            else:
                if layer_cfg.get("property_name") == feature.get("layerName"):
                    mapped_values.append(layer_cfg.get("target_harmonized_value"))

        # Helping function to identify issues. Only "harmonized_value is useful for frontend application"
        layer_results.append(
            {
                "layer": layer_name,
                "property_name": property_name,
                "value": value,
                "description": description,
            }
        )

    # property_values variable contains the mapping between attribute value and drillapi categories (1,2,3)

    if mapped_values:
        harmonized_value = max(mapped_values)

    # If no value is found, fallback value is = 4
    if not harmonized_value:
        harmonized_value = 4

    return {
        "layer_results": layer_results,
        "harmonized_value": harmonized_value,
    }
