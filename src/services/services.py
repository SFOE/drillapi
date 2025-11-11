import httpx
import json
import xml.etree.ElementTree as ET
from fastapi import HTTPException


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
            return json.loads(text)
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

            return features
        except Exception as e:
            raise HTTPException(500, detail=f"Failed to parse GML WMS response: {e}")

    else:
        # fallback: return raw text
        return {"raw": text}
