from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..services import security
from ..routes.cantons import get_cantons_data, filter_active_cantons
from ..config import settings

from ..routes.drill_category import get_drill_category

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
            error_msg = f"Canton '{canton}' not found or inactive."
            return templates.TemplateResponse(
                "checker.html",
                {
                    "request": request,
                    "canton": canton,
                    "results": [],
                    "error_msg": error_msg,
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
                resp_json = await get_drill_category(
                    request=request, coord_x=x, coord_y=y
                )

                result["status"] = 200
                result["success"] = resp_json.get("status") == "success"
                result["content"] = resp_json

                calculated = None
                if resp_json.get("ground_category"):
                    calculated = resp_json["ground_category"].get("harmonized_value")

                if calculated == control_harmonized_value:
                    result["control_harmonized_values"] = "success"
                    result["control_harmonized_values_message"] = (
                        "Harmonized value matches control value."
                    )
                else:
                    result["control_harmonized_values"] = "error"
                    result["control_harmonized_values_message"] = (
                        f"❌ Harmonized value mismatch at coordinates ({x},{y}): "
                        f"expected '{control_harmonized_value}', got '{calculated}'"
                    )

            except Exception as e:
                result["error"] = str(e)

            results.append(result)

    return templates.TemplateResponse(
        "checker.html",
        {"request": request, "canton": canton, "results": results, "error_msg": None},
    )
