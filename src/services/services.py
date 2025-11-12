import httpx
import json
import xml.etree.ElementTree as ET
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


# -----------------------------
# Encoding / Normalization Utils
# -----------------------------
def normalize_string(value: str) -> str:
    """
    Fix common double-encoding issues from WMS responses.
    """
    if not isinstance(value, str):
        return value
    try:
        # decode double UTF-8 encoded strings
        return value.encode("latin1").decode("utf-8")
    except UnicodeEncodeError:
        return value
    except UnicodeDecodeError:
        return value


def normalize_feature(feat):
    """
    Safely normalize a feature dict or string.
    """
    if isinstance(feat, dict):
        return {k: normalize_string(v) for k, v in feat.items()}
    return normalize_string(feat)


# -----------------------------
# Canton Lookup
# -----------------------------
def get_canton_from_coordinates(coord_x: float, coord_y: float):
    """
    Query geo.admin.ch to find the canton for coordinates in EPSG:2056.
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
        raise HTTPException(500, detail=f"Failed to fetch canton: {e}")

    return payload.get("results", [])


# -----------------------------
# Fetch WMS / ESRI Features
# -----------------------------
async def fetch_features_for_point(coord_x: float, coord_y: float, config: dict):
    """
    Fetch features at a given coordinate using WMS GetFeatureInfo or ESRI REST Feature service.
    Returns a list of normalized feature dicts.
    """
    info_format = config["infoFormat"].lower()
    features = []

    async with httpx.AsyncClient(timeout=20.0) as client:

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
                logger.info("ESRI request: %s %s", esri_url, params)
                resp = await client.get(esri_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                raw_features = data.get("features", [])
                # Normalize
                for feat in raw_features:
                    attr = feat.get("attributes", {})
                    features.append(normalize_feature(attr))

        else:
            # WMS GetFeatureInfo
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
            }
            wms_url = config["wmsUrl"]
            logger.info("WMS request: %s %s", wms_url, params_wms)
            resp = await client.get(wms_url, params=params_wms)
            resp.raise_for_status()
            raw_features = await parse_wms_getfeatureinfo(
                resp.content, config["infoFormat"]
            )
            # Normalize
            features.extend([normalize_feature(f) for f in raw_features])

    return features


# -----------------------------
# Parse WMS GetFeatureInfo
# -----------------------------
async def parse_wms_getfeatureinfo(content: bytes, info_format: str):
    text = content.decode("utf-8")
    info_format = info_format.lower()

    if "arcgis/json" in info_format or "json" in info_format:
        try:
            data = json.loads(text)
            features = []

            if "features" in data and isinstance(data["features"], list):
                for feat in data["features"]:
                    attr = feat.get("attributes", {}) if isinstance(feat, dict) else {}
                    features.append(attr)
            else:
                features = data if isinstance(data, list) else []
            return features
        except Exception as e:
            raise HTTPException(500, detail=f"Failed to parse JSON response: {e}")

    elif "gml" in info_format or "xml" in info_format:
        try:
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
        except Exception as e:
            raise HTTPException(500, detail=f"Failed to parse GML response: {e}")

    else:
        raise HTTPException(500, detail=f"Unsupported infoFormat: {info_format}")


# -----------------------------
# Process Ground Categories
# -----------------------------
def process_ground_category(
    ground_features: list, config_layers: list, harmony_map: list
):
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
            # Handle dict or string
            raw_value = (
                feature.get(property_name) if isinstance(feature, dict) else feature
            )
            if not raw_value:
                continue
            value = normalize_string(raw_value)
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

    # Harmonize sum
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
