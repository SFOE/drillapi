import httpx
import json
import xml.etree.ElementTree as ET
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


def get_canton_from_coordinates(coord_x: float, coord_y: float):
    """
    Query geo.admin.ch to find the canton for coordinates in EPSG:2056.
    Returns a list of results (dictionaries) or empty list if not found.
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
        raise HTTPException(500, detail=f"Failed to fetch canton from coordinates: {e}")

    return payload.get("results", [])


async def fetch_features_for_point(coord_x: float, coord_y: float, config: dict):
    """
    Fetch features at a given coordinate using either WMS GetFeatureInfo or ESRI REST Feature service
    depending on config['infoFormat'].
    Returns a list of feature dicts.
    """
    info_format = config["infoFormat"].lower()
    features = []

    async with httpx.AsyncClient(timeout=20.0) as client:

        if info_format == "arcgis/json":
            layers_list = [layer["name"] for layer in config["layers"]]

            for layer_name in layers_list:
                esri_url = f"{config['wmsUrl'].rstrip('/')}/{layer_name}/query"
                params = {
                    "geometry": f"{coord_x},{coord_y}",
                    "geometryType": "esriGeometryPoint",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "f": "json",
                }
                logger.info("ESRI Feature request: %s %s", esri_url, params)
                resp = await client.get(esri_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                features.extend(data.get("features", []))

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
            features = await parse_wms_getfeatureinfo(resp.content, config["infoFormat"])

    return features


async def parse_wms_getfeatureinfo(content: bytes, info_format: str):
    """
    Parse WMS GetFeatureInfo response content depending on infoFormat.
    Supports JSON, GeoJSON, GML/XML.
    Returns a Python dict (for JSON) or list of feature dictionaries (for GML).
    """
    text = content.decode("utf-8")
    info_format = info_format.lower()

    if "json" in info_format:
        try:
            features = json.loads(text)
            if not features:
                logger.warning("WMS JSON response is empty")
            return features
        except Exception as e:
            raise HTTPException(500, detail=f"Failed to parse JSON WMS response: {e}")

    elif "gml" in info_format or "xml" in info_format:
        try:
            root = ET.fromstring(text)
            features = []

            # Common GML namespace
            ns = {"gml": "http://www.opengis.net/gml"}

            for feature_member in root.findall(".//gml:featureMember", ns):
                feature_data = {}
                for child in feature_member.iter():
                    if "}" in child.tag:
                        tag = child.tag.split("}", 1)[1]  # remove namespace
                    else:
                        tag = child.tag
                    feature_data[tag] = child.text
                features.append(feature_data)

            if not features:
                logger.warning("WMS GML response contains no features")
            return features

        except Exception as e:
            raise HTTPException(500, detail=f"Failed to parse GML WMS response: {e}")

    else:
        # Treat unknown/raw formats as errors
        raise HTTPException(
            500, detail=f"Unsupported WMS info format or raw response: {text}"
        )


def process_ground_category(
    ground_features: list, config_layers: list, harmony_map: list
):
    """
    Process raw WMS features into structured ground category values per canton config.

    Args:
        ground_features: List of dicts returned by parse_wms_getfeatureinfo.
        config_layers: List of layer configs, each with 'name', 'propertyName', 'propertyValues'.
        harmony_map: Mapping of value to end, harmonized ones.

    Returns:
        List of dicts: [{"layer": layer_name, "propertyName": str, "value": str}, ...]
    """
    result = []

    for layer_cfg in config_layers:
        layer_name = layer_cfg.get("name")
        property_name = layer_cfg.get("propertyName")
        property_values = layer_cfg.get("propertyValues", [])

        summand = None

        # Find matching feature
        for feature in ground_features:
            original_ground_category = feature[property_name]

            for item in property_values:
                if item["name"] == original_ground_category:
                    summand = item["summand"]
                    description = item["desc"]
                    break

            # TODO: harmonize data using harmony_map

        result.append(
            {
                "layer": layer_name,
                "propertyName": property_name,
                "summand": summand,
                "description": description,
            }
        )

    return result
