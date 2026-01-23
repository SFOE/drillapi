from fastapi import APIRouter, Request, Path
from drillapi.cantons_configuration import cantons
from ..services import processing, security
from ..services.error_handler import handle_errors
from ..config import settings
from ..models.models import SuitabilityFeature, GroundCategory, ResultDetail
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/v1/drill-category/{coord_x}/{coord_y}",
    response_model=SuitabilityFeature,
)
@security.limiter.limit(settings.RATE_LIMIT)
@handle_errors
async def get_drill_category(
    request: Request,
    coord_x: float = Path(..., gt=2400000, le=2900000),
    coord_y: float = Path(..., gt=1070000, le=1300000),
):
    """Return drill category at a given coordinate using WMS GetFeatureInfo or ESRI REST feature service."""

    # Default "no info" feature
    suitability_feature = SuitabilityFeature(
        coord_x=coord_x,
        coord_y=coord_y,
        canton="",
        canton_config=None,
        ground_category=GroundCategory(
            layer_results=[],
            source_values="",
        ),
        status="error",
        result_detail=ResultDetail(
            message="",
            full_url="",
        ),
    )

    # Determine canton from coordinates using GeoadminAPI   
    canton_result = await processing.get_canton_from_coordinates(coord_x, coord_y)

    if not canton_result:
        message = (
            f"No canton found for coordinates using GeoadminAPI: ({coord_x}, {coord_y})"
        )
        logger.warning(message)
        suitability_feature.result_detail.message = message
        return suitability_feature

    code_canton = canton_result[0]["attributes"]["ak"]
    canton_config = cantons.CANTONS["cantons_configurations"].get(code_canton)

    if not canton_config:
        logger.error(
            "No configuration for canton %s at (%s, %s)",
            code_canton,
            coord_x,
            coord_y,
        )
        suitability_feature.result_detail.message = (
            "No configuration available for this canton."
        )
        return suitability_feature

    # Fill canton data
    suitability_feature.canton = code_canton
    suitability_feature.canton_config = canton_config

    # Fetch features (WMS or ESRI REST) and process into feature
    result = await processing.fetch_features_for_point(coord_x, coord_y, canton_config)

    # Feature(s) found, process to reclassification
    processed_ground_category = processing.process_ground_category(
        result["features"],
        canton_config["layers"],
    )

    # Fill the model
    suitability_feature.ground_category = processed_ground_category
    suitability_feature.status = "success"
    suitability_feature.result_detail = ResultDetail(
        message="Success",
        full_url=result["full_url"],
        detail=result["error"],
    )

    return suitability_feature
