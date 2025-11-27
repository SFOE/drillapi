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
            if "arcgis" in info_format:
                for layer in config["layers"]:
                    layer_id = layer.get("id")
                    if layer_id is None:
                        raise RuntimeError(
                            "Layer config missing 'id' for ESRI REST service"
                        )

                    esri_url = f"{config['wmsUrl'].rstrip('/')}/{layer_id}/query"

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
                delta = 10
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
                    "INFO_FORMAT": config.get("infoFormat", "text/plain"),
                    "I": str(i),
                    "J": str(j),
                    "CRS": "EPSG:2056",
                    "WIDTH": str(width),
                    "HEIGHT": str(height),
                    "BBOX": bbox,
                    "STYLES": config.get("style", ""),
                    "FEATURE_COUNT": config.get("feature_count", 10),
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
                    features = await parse_wms_getfeatureinfo(
                        resp.content, config["infoFormat"]
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
# PARSE WMS OR ESRI JSON RESPONSES
# ============================================================
async def parse_wms_getfeatureinfo(content: bytes, info_format: str):
    """
    Unified parser for:
    • ESRI REST (arcgis/json, application/json, json)
    • WMS GetFeatureInfo (GML/XML)
    • MapServer msGMLOutput (<*_feature>)
    • Standard GML (<gml:featureMember>)
    """
    text = content.decode("utf-8", errors="ignore")
    info_format = (info_format or "").lower().strip()

    # ----------------------------------------------------------------------
    # JSON / ESRI REST PARSING
    # ----------------------------------------------------------------------
    if "json" in info_format or "arcgis" in info_format:
        try:
            data = json.loads(text)
        except Exception as e:
            raise HTTPException(500, f"Invalid JSON: {e}")

        features = []

        # (A) ArcGIS FeatureServer standard response
        # ------------------------------------------------
        if isinstance(data, dict) and "features" in data:
            feats = data.get("features") or []  # may be null
            for feat in feats:
                if not isinstance(feat, dict):
                    continue

                # typical structure: { "attributes": {..}, "geometry": {...} }
                if "attributes" in feat and isinstance(feat["attributes"], dict):
                    features.append(feat["attributes"])
                else:
                    # fallback: flatten feature
                    features.append(
                        {k: v for k, v in feat.items() if not isinstance(v, dict)}
                    )
            return features

        # (B) Single ESRI feature: { "attributes": {...} }
        # ------------------------------------------------
        if isinstance(data, dict) and "attributes" in data:
            return [data["attributes"]]

        # (C) Plain JSON list of objects
        # ------------------------------------------------
        if isinstance(data, list):
            out = []
            for item in data:
                if isinstance(item, dict) and "attributes" in item:
                    out.append(item["attributes"])
                else:
                    out.append(item)
            return out

        # (D) fallback → return raw object
        return [data]

    # ----------------------------------------------------------------------
    # XML/GML WMS GetFeatureInfo PARSING
    # ----------------------------------------------------------------------
    try:
        root = ET.fromstring(text)
    except Exception as e:
        raise HTTPException(500, f"Invalid XML/GML: {e}")

    ns = {"gml": "http://www.opengis.net/gml"}
    features = []

    # ----------------------------------------------------------------------
    # (1) Standard GML <gml:featureMember>
    # ----------------------------------------------------------------------
    for fm in root.findall(".//gml:featureMember", ns):
        fdict = {}
        for el in fm.iter():
            tag = el.tag.split("}", 1)[-1]
            # skip geometry
            if tag.lower() in ("boundedby", "geometry", "polygon", "multipolygon"):
                continue
            if el.text and el.text.strip():
                fdict[tag] = el.text.strip()
        if fdict:
            features.append(fdict)

    # ----------------------------------------------------------------------
    # (2) MapServer msGMLOutput  <*_feature>
    # ----------------------------------------------------------------------
    import re

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

    return features


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
