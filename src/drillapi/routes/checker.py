from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from collections import defaultdict
import logging
from ..services import security
from ..routes.cantons import get_cantons_data, filter_active_cantons
from ..config import settings

from ..routes.drill_category import get_drill_category
from ..models.models import GroundCategory, CheckerResult

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/checker/", response_class=HTMLResponse)
@security.limiter.limit(settings.RATE_LIMIT)
@router.get("/checker/{canton}", response_class=HTMLResponse)
async def checker_page(request: Request, canton: str | None = None):
    """
    Perform checks for all or a single canton and render HTML with results.
    """

    logger.info(f"CHECKER: started for canton: {canton}")

    canton = canton.upper().strip() if canton else ""

    full_config = get_cantons_data()
    active_config = filter_active_cantons(full_config)

    if canton:
        if canton not in active_config:

            logger.info(f"CHECKER: No configuration for canton: {canton}")

            return templates.TemplateResponse(
                "checker.html",
                {
                    "request": request,
                    "canton": canton,
                    "results": [],
                    "error_msg": f"Canton '{canton}' not found or inactive.",
                },
            )
        config = {canton: active_config[canton]}
    else:
        logger.info(f"CHECKER: started for all active cantons")
        config = active_config

    results = []

    for canton_code, data in config.items():
        logger.info(f"CHECKER: Running for canton: {canton}")
        for location in data["ground_control_point"]:

            x = location[0]
            y = location[1]
            control_harmonized_value = location[2]
            url = f"/v1/drill-category/{x}/{y}"

            # Empty result, error by default
            result = CheckerResult(
                canton=canton_code,
                url=url,
                control_status="error",
                control_status_message="No info, script error",
            )

            try:

                logger.info(f"CHECKER: getting drill category for : {x}/{y}")

                feature = await get_drill_category(
                    request=request,
                    coord_x=x,
                    coord_y=y,
                )

                calculated = (
                    feature.ground_category.harmonized_value
                    if feature.ground_category
                    else None
                )

                result.content_for_template = feature

                if calculated == control_harmonized_value:

                    logger.info(
                        f"CHECKER: ground control successful for canton {canton} at coordinates {x}/{y}"
                    )

                    result.control_status = "success"
                    result.control_status_message = f"Harmonized {control_harmonized_value} value matches control value {calculated}."

                else:

                    logger.warning(
                        f"CHECKER: ground control NOT successful for canton {canton} at coordinates {x}/{y}"
                    )

                    result.control_status = "error"
                    result.control_status_message = f"❌ Harmonized value mismatch at coordinates ({x}, {y}): expected '{control_harmonized_value}', got '{calculated}'"

            except Exception as e:
                logger.error(
                    f"CHECKER: error for canton {canton} at coordinates {x}/{y}. Error message: {e}"
                )

            results.append(result)

    return templates.TemplateResponse(
        "checker.html",
        {
            "request": request,
            "canton": canton,
            "results": results,
        },
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
