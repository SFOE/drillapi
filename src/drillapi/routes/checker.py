from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..services import security
from ..routes.cantons import get_cantons_data, filter_active_cantons
from ..config import settings

from ..routes.drill_category import get_drill_category
from ..models.models import GroundCategory

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/checker/", response_class=HTMLResponse)
@security.limiter.limit(settings.RATE_LIMIT)
@router.get("/checker/{canton}", response_class=HTMLResponse)
async def checker_page(request: Request, canton: str | None = None):
    """
    Perform checks for all or a single canton and render HTML with results.
    """
    canton = canton.upper().strip() if canton else ""

    full_config = get_cantons_data()
    active_config = filter_active_cantons(full_config)

    if canton:
        if canton not in active_config:
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
        config = active_config

    results = []

    for canton_code, data in config.items():
        for location in data["ground_control_point"]:
            x = location[0]
            y = location[1]
            control_harmonized_value = location[2]

            url = f"/v1/drill-category/{x}/{y}"
            result = {"canton": canton_code, "url": url}

            try:
                # Call the drill category endpoint
                feature = await get_drill_category(
                    request=request,
                    coord_x=x,
                    coord_y=y,
                )

                # ✅ Ensure ground_category is a Pydantic model
                if isinstance(feature.ground_category, dict):
                    feature.ground_category = GroundCategory(**feature.ground_category)

                # Use a plain dict for template
                feature_dict = feature.model_dump()

                result.update(
                    status=200,
                    success=feature.status == "success",
                    content_for_template=feature_dict,
                )

                # Harmonized value
                calculated = (
                    feature.ground_category.harmonized_value
                    if feature.ground_category
                    else None
                )

                if calculated == control_harmonized_value:
                    result["control_harmonized_values"] = "success"
                    result["control_harmonized_values_message"] = (
                        "Harmonized value matches control value."
                    )
                else:
                    result["control_harmonized_values"] = "error"
                    result["control_harmonized_values_message"] = (
                        f"❌ Harmonized value mismatch at coordinates ({x}, {y}): "
                        f"expected '{control_harmonized_value}', got '{calculated}'"
                    )

            except Exception as e:
                result.update(
                    status=500,
                    success=False,
                    error=str(e),
                )

            results.append(result)

    # ✅ Simplified canton grouping
    canton_groups = {}
    for r in results:
        canton_groups.setdefault(r["canton"], []).append(r)

    return templates.TemplateResponse(
        "checker.html",
        {
            "request": request,
            "canton": canton,
            "results": results,
            "canton_groups": canton_groups,
            "error_msg": None,
        },
    )
