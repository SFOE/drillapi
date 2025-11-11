import json
from typing import Annotated
import logging
import asyncio
from fastapi import FastAPI, Path, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse

from settings_values import cantons, globals
from src.services import get_canton_from_coordinates, verify_ip

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
from typing import Optional

import geopandas as gpd
from shapely.geometry import Point


logging.basicConfig(
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)


# Create rate limiter
limiter = Limiter(key_func=get_remote_address)


# start the app
app = FastAPI()

# Register exception handler for rate limit errors
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/v1/drill-category/{coord_x}/{coord_y}")
@limiter.limit(globals.RATE_LIMIT)
async def get_drill_category(
    request: Request,
    coord_x: Annotated[
        float,
        Path(title="X coordinate of the location in EPSG:2056", gt=2400000, le=2900000),
    ],
    coord_y: Annotated[
        float,
        Path(title="Y coordinate of the location in EPSG:2056", gt=1070000, le=1300000),
    ],
):

    # Get canton corresponding to the coordinates using geoadmin api
    canton = get_canton_from_coordinates(coord_x, coord_y)

    code_canton = canton[0]["attributes"]["ak"]

    # TODO: replace by local cantons geojson for better performance ?
    config = cantons.CANTONS["cantons_configurations"].get(code_canton)

    if not config:
        raise HTTPException(
            status_code=404, detail=f"Configuration for canton {code_canton} not found!"
        )

    # Calculate BBOX around the point (e.g. 20x20m square)
    delta = 10  # meters
    bbox = f"{coord_x - delta},{coord_y - delta},{coord_x + delta},{coord_y + delta}"

    # WMS request parameters for ground category
    wms_url = config["wmsUrl"]
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

    logging.info(f"Request base URL: {wms_url}")
    logging.info(f"Request params: {params_wms}")

    # results initialisation
    ground_type = None
    in_consultation = False

    # Request for ground type
    with httpx.Client(timeout=20.0) as client:
        response_ground = client.get(wms_url, params=params_wms)
        response_ground.raise_for_status()
        try:  # If response content can't be processed, need to raise error
            # TODO: use strong typing for expected response
            geojson_data = response_ground.json()
            features = geojson_data.get("features", [])
        except:
            # If canton's WMS backend changes, raise explicit error to help adapting configuration
            # Important to raise 404 even if canton's backend return 202: response is not valid!
            raise HTTPException(
                status_code=404,
                detail=f"Bad request for  {code_canton}: {response_ground.content}",
            )

        if features:
            properties = features[0].get("properties", {})
            ground_type = properties.get("Type", "Type inconnu")
        else:
            ground_type = "Information not available."

    # Verify intersection with consultation area if applicable
    # gdf = gpd.read_file("data/rohrleitungen_konsultationsbereich.gpkg")
    # gdf = gdf.to_crs(epsg=2056)
    # point = Point(coord_x, coord_y)
    # in_consultation = gdf.intersects(point).any()

    return {
        "coord_x": coord_x,
        "coord_y": coord_y,
        "canton": code_canton,
        "ground_category": ground_type,
        "in_consultation_area": in_consultation,
    }


def get_cantons_data():
    """Shared logic to get cantons dictionary"""
    return cantons.CANTONS["cantons_configurations"]


# Route 1: all cantons
@app.get("/v1/cantons")
@limiter.limit(globals.RATE_LIMIT)
async def get_all_cantons(request: Request):
    """Return all canton entries."""
    return get_cantons_data()


# Route 2: specific canton by code
@app.get("/v1/cantons/{code}")
@limiter.limit(globals.RATE_LIMIT)
async def get_canton_by_code(
    request: Request,
    code: str = Path(
        ..., min_length=2, max_length=2, description="Two-letter canton code"
    ),
):
    """Return a specific canton by its 2-letter code (e.g., 'ZH', 'BE')."""
    code = code.upper()
    cantons_dict = get_cantons_data()
    if code not in cantons_dict:
        raise HTTPException(status_code=404, detail=f"Canton '{code}' not found")
    return {code: cantons_dict[code]}


@app.get("/checker/", dependencies=[Depends(verify_ip)])
async def checker(request: Request):
    """
    Check the availability of canton drilling services and stream progress updates.

    This endpoint iterates over the configured cantons and their sample locations
    to verify that each corresponding drilling category service endpoint responds
    successfully.

    The response is streamed progressively in plain text format so that the client
    can observe real-time progress updates while the checks are being performed.
    Each canton and location will output its status as it is verified.

    ---
    **Access Control:**
    Only whitelisted IP addresses defined in `ALLOWED_IPS` are allowed to access
    this route.

    **Response Type:**
    `text/plain` — streamed lines indicating progress and final results.

    **Example Output:**
    ```
    Checking service availability for Zurich
      - Checking location (2500000, 1200000) ... ✅ OK
      - Checking location (2600000, 1250000) ... ❌ Failed (404)
    Finished Zurich: ❌ Failed

    All checks completed.
    ```
    """

    config = cantons.CANTONS["cantons_configurations"]
    results = {}

    async def progress_generator():
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for canton, data in config.items():
                canton_success = True
                yield f"Checking service availability for {canton}\n"

                for location in data["exampleLocation"]:
                    url = f"/v1/drill-category/{location[0]}/{location[1]}"
                    yield f"  - Checking location {url} ... "
                    try:
                        resp = await client.get(url, timeout=60.0)
                        if resp.status_code == 200:
                            yield "✅ OK\n"
                        else:
                            canton_success = False
                            yield f"❌ Failed ({resp.status_code})\n"
                    except Exception as e:
                        canton_success = False
                        yield f"❌ Error: {e}\n"

                results[canton] = canton_success
                yield f"Finished {canton}: {'✅ OK' if canton_success else '❌ Failed'}\n\n"

        yield "All checks completed.\n"

    return StreamingResponse(progress_generator(), media_type="text/plain")
