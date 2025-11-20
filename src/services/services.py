import httpx
import json
import xml.etree.ElementTree as ET
from fastapi import HTTPException
import logging

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


def normalize_feature(feat):
    """
    Normalize every string value in a feature dict.
    """
    if isinstance(feat, dict):
        return {k: normalize_string(v) for k, v in feat.items()}
    return normalize_string(feat)


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
      - ESRI REST Feature Service (infoFormat='arcgis/json'), or
      - WMS GetFeatureInfo for other formats.

    Returns:
        dict: {
            "features": [...],
            "full_url": str,
            "error": Optional[str]
        }
    """
    info_format = config["infoFormat"].lower()
    features = []
    full_url = ""
    error_message = None

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            # ---------- ESRI REST Feature Service ----------
            if info_format == "arcgis/json":
                for layer in config["layers"]:
                    layer_name = layer["name"]
                    esri_url = f"{config['wmsUrl'].rstrip('/')}/{layer_name}/query"
                    params = {
                        "geometry": f"{coord_x},{coord_y}",
                        "geometryType": "esriGeometryPoint",
                        "spatialRel": "esriSpatialRelIntersects",
                        "outFields": "*",
                        "f": "json",
                    }

                    try:
                        resp = await client.get(esri_url, params=params)
                        full_url = str(resp.request.url)
                        resp.raise_for_status()
                    except Exception as e:
                        error_message = f"ESRI request failed: {e}"
                        logger.error("%s — URL: %s", error_message, full_url)
                        continue

                    try:
                        data = resp.json()
                    except Exception as e:
                        snippet = resp.text[:200]
                        error_message = f"Invalid JSON for {full_url}: {e} ({snippet})"
                        logger.error(error_message)
                        continue

                    raw_features = data.get("features", [])
                    for feat in raw_features:
                        if isinstance(feat, dict):
                            attr = feat.get("attributes", {})
                            features.append(normalize_feature(attr))

            # ---------- WMS GetFeatureInfo ----------
            else:
                delta = 10
                bbox = f"{coord_x - delta},{coord_y - delta},{coord_x + delta},{coord_y + delta}"
                layers_list = ",".join([layer["name"] for layer in config["layers"]])
                params_wms = {
                    "SERVICE": "WMS",
                    "VERSION": "1.3.0",
                    "REQUEST": "GetFeatureInfo",
                    "QUERY_LAYERS": layers_list,
                    "LAYERS": layers_list,
                    "INFO_FORMAT": config["infoFormat"],
                    "I": "50",
                    "J": "50",
                    "CRS": "EPSG:2056",
                    "WIDTH": "101",
                    "HEIGHT": "101",
                    "BBOX": bbox,
                    "STYLES": "default",
                }

                wms_url = config["wmsUrl"]
                try:
                    resp = await client.get(wms_url, params=params_wms)
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
                    raw_features = await parse_wms_getfeatureinfo(
                        resp.content, config["infoFormat"]
                    )
                    features.extend([normalize_feature(f) for f in raw_features])
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
# PARSE WMS OR ESRI JSON RESPONSES
# ============================================================
async def parse_wms_getfeatureinfo(content: bytes, info_format: str):
    """
    Parse WMS GetFeatureInfo or ESRI REST JSON response into Python dicts.
    """
    text = content.decode("utf-8", errors="ignore")
    info_format = info_format.lower()

    try:
        # ArcGIS REST JSON or GeoJSON
        if "json" in info_format:
            data = json.loads(text)
            features = []

            # ESRI REST-style
            if isinstance(data, dict) and "features" in data:
                for feat in data["features"]:
                    attr = feat.get("attributes", {}) if isinstance(feat, dict) else {}
                    features.append(attr)

            # Plain array of features
            elif isinstance(data, list):
                features = data
            else:
                features = [data] if data else []

            return features

        # GML/XML
        elif "gml" in info_format or "xml" in info_format:
            root = ET.fromstring(text)
            ns = {"gml": "http://www.opengis.net/gml"}
            features = []

            for feature_member in root.findall(".//gml:featureMember", ns):
                feature_data = {}
                for child in feature_member.iter():
                    tag = child.tag.split("}", 1)[1] if "}" in child.tag else child.tag
                    feature_data[tag] = child.text
                features.append(feature_data)

            return features

        else:
            raise ValueError(f"Unsupported infoFormat: {info_format}")

    except Exception as e:
        logger.error("Error parsing WMS/ESRI response: %s", e)
        raise HTTPException(500, detail=f"Failed to parse WMS/ESRI response: {e}")


# ============================================================
# PROCESS + HARMONIZE GROUND CATEGORIES
# ============================================================
def process_ground_category(
    ground_features: list, config_layers: list, harmony_map: list
):
    """
    Process raw features into harmonized ground category values per canton configuration.
    Returns:
        dict: {
            "layer_results": [...],
            "mapping_sum": int,
            "harmonized_value": int
        }
    """
    layer_results = []
    mapping_sum = 0

    for layer_cfg in config_layers:
        layer_name = layer_cfg.get("name")
        property_name = layer_cfg.get("propertyName")
        property_values = layer_cfg.get("propertyValues", [])

        layer_summand = 0
        description = None
        last_value = None

        for feature in ground_features:
            value = feature.get(property_name) if isinstance(feature, dict) else feature
            if not value:
                continue

            value = normalize_string(value)
            last_value = value

            for item in property_values:
                if item.get("name") == value:
                    layer_summand += item.get("summand", 0)
                    description = item.get("desc")
                    break

        mapping_sum += layer_summand

        layer_results.append(
            {
                "layer": layer_name,
                "propertyName": property_name,
                "value": last_value,
                "summand": layer_summand,
                "description": description,
            }
        )

    # Harmonization: map sum → harmonized value
    harmonized_value = None
    if harmony_map:
        match = next((h["value"] for h in harmony_map if h["sum"] == mapping_sum), None)
        harmonized_value = (
            match if match is not None else (4 if mapping_sum == 0 else None)
        )

    return {
        "layer_results": layer_results,
        "mapping_sum": mapping_sum,
        "harmonized_value": harmonized_value,
    }
