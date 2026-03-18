from fastapi import APIRouter, Request, Query, Path
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
    exclude_inactive_cantons: bool = Query(
        True,
        alias="exclude-inactive-cantons",
        description="If false, inactive cantons are also used.",
    ),
):
    """Return drill category at a given coordinate using WMS GetFeatureInfo or ESRI REST feature service."""

    # Default feature for selected coordinates
    suitability_feature = SuitabilityFeature(
        coord_x=coord_x,
        coord_y=coord_y,
        ground_category=GroundCategory(),
        result_detail=ResultDetail(),
    )

    # Determine canton from coordinates using GeoadminAPI
    canton_result = await processing.get_canton_from_coordinates(coord_x, coord_y)

    if not canton_result:
        message = (
            f"No canton found for coordinates using GeoadminAPI: ({coord_x}, {coord_y})"
        )
        logger.warning(message)
        # Not in Switzerland
        suitability_feature.ground_category.harmonized_value = 6
        suitability_feature.result_detail.message = message
        return suitability_feature

    code_canton = canton_result[0]["attributes"]["ak"]
    canton_config = cantons.CANTONS["cantons_configurations"].get(code_canton)

    suitability_feature.canton = code_canton
    suitability_feature.canton_config = canton_config

    is_missing_config = canton_config is None
    is_active = canton_config.get("active", False) if canton_config else False

    # Exclude inactive or missing cantons
    # Inactive cantons are activated when called from checker in order to help debug network issues
    if exclude_inactive_cantons and (is_missing_config or not is_active):
        logger.warning(
            "No configuration for canton %s at (%s, %s) or inactive canton",
            code_canton,
            coord_x,
            coord_y,
        )

        suitability_feature.ground_category.harmonized_value = 5
        suitability_feature.result_detail.message = "Canton not active or not existing"
        return suitability_feature

    # Fetch features (WMS or ESRI REST) from external geoservices and process into feature
    result = await processing.fetch_features_for_point(coord_x, coord_y, canton_config)

    # Feature(s) found, process to reclassification
    processed_ground_category = processing.process_ground_category(
        result["features"],
        canton_config["layers"],
    )

    # Fill the model with full data - all process worked for this location
    suitability_feature.ground_category = processed_ground_category
    suitability_feature.result_detail = ResultDetail(
        message="Success",
        full_url=result["full_url"],
        detail=result["error"],
    )
    return suitability_feature
