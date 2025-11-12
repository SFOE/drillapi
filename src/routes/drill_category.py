from fastapi import APIRouter, Request, Path, HTTPException
from settings_values import cantons
from src.services import services, security
from src.services.error_handler import handle_errors
import httpx
import logging
from src.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/v1/drill-category/{coord_x}/{coord_y}")
@security.limiter.limit(settings.RATE_LIMIT)
@handle_errors
async def get_drill_category(
    request: Request,
    coord_x: float = Path(..., gt=2400000, le=2900000),
    coord_y: float = Path(..., gt=1070000, le=1300000),
):
    """Return ground category at a given coordinate using WMS GetFeatureInfo."""

    # --- Your previous code remains almost identical ---
    canton_result = services.get_canton_from_coordinates(coord_x, coord_y)
    if not canton_result:
        raise HTTPException(404, detail="No canton found for these coordinates")

    code_canton = canton_result[0]["attributes"]["ak"]
    config = cantons.CANTONS["cantons_configurations"].get(code_canton)
    if not config:
        raise HTTPException(404, f"Configuration for canton {code_canton} not found!")

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

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(wms_url, params=params_wms)
        resp.raise_for_status()
        ground_category = await services.parse_wms_getfeatureinfo(
            resp.content, config["infoFormat"]
        )

    ground_category = services.process_ground_category(
        ground_category, config["layers"], config["harmonyMap"]
    )

    return {
        "coord_x": coord_x,
        "coord_y": coord_y,
        "canton": code_canton,
        "ground_category": ground_category,
        "status": "success",
        "wms_url": wms_url,
        "wms_params": params_wms,
    }
