from fastapi import APIRouter, Request, Path, HTTPException
from settings_values import cantons
from src.services import services, security
from src.services.error_handler import handle_errors  # your decorator
from src.config import settings
import logging

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
    """Return ground category at a given coordinate using WMS GetFeatureInfo or ESRI REST feature service."""

    # --- Determine canton from coordinates ---
    canton_result = services.get_canton_from_coordinates(coord_x, coord_y)
    if not canton_result:
        raise HTTPException(404, detail="No canton found for these coordinates")

    code_canton = canton_result[0]["attributes"]["ak"]
    config = cantons.CANTONS["cantons_configurations"].get(code_canton)
    if not config:
        raise HTTPException(
            404, detail=f"Configuration for canton {code_canton} not found!"
        )

    # --- Fetch features (WMS or ESRI REST) ---
    features = await services.fetch_features_for_point(coord_x, coord_y, config)

    if not features:
        status = "error"
        error_detail = {
            "message": "No features returned from WMS or ESRI service",
        }
    else:
        status = "success"
        error_detail = None
        # --- Process features into ground category ---
        features = services.process_ground_category(
            features, config["layers"], config["harmonyMap"]
        )

    return {
        "coord_x": coord_x,
        "coord_y": coord_y,
        "canton": code_canton,
        "ground_category": features,
        "status": status,
        "error": error_detail,
    }
