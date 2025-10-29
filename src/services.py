import httpx


def get_canton_from_coordinates(coord_x: float, coord_y: float):
    """
    Query geo.admin.ch to find the canton for coordinates in EPSG:2056.
    Returns the canton name (string) or None if not found.
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

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()

    result = payload.get("results", [])

    return result
