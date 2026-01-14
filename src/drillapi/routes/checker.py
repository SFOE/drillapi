from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..services import security

import httpx
import asyncio
import json

from ..routes.cantons import get_cantons_data, filter_active_cantons
from ..config import settings

router = APIRouter()

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@router.get("/checker/", response_class=HTMLResponse)
@security.limiter.limit(settings.RATE_LIMIT)
@router.get("/checker/{canton}", response_class=HTMLResponse)
async def checker_page(request: Request, canton: str | None = None):

    canton = canton.upper() if canton else ""

    return templates.TemplateResponse(
        "checker_ws.html", {"request": request, "canton": canton}
    )


@router.websocket("/checker/ws")
async def checker_websocket(ws: WebSocket):
    """
    WebSocket endpoint:
        - accepts: {"canton": "VD"} or {"canton": ""}
        - streams JSON results as checks are performed
    """

    await ws.accept()

    try:
        init_msg = await ws.receive_text()
        payload = json.loads(init_msg)
        canton = payload.get("canton", "").strip().upper()

        full_config = get_cantons_data()
        active_config = filter_active_cantons(full_config)

        if canton:
            if canton not in active_config:
                await ws.send_json(
                    {"error": f"Canton '{canton}' not found or inactive."}
                )
                await ws.close()
                return
            config = {canton: active_config[canton]}
        else:
            config = active_config

        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for canton_code, data in config.items():
                for location in data["ground_control_point"]:
                    x = location[0]
                    y = location[1]
                    url = f"/v1/drill-category/{x}/{y}"
                    result = {"canton": canton_code, "url": url}

                    try:
                        resp = await client.get(url, timeout=60.0)
                        result["status"] = resp.status_code

                        try:
                            body = resp.json()
                        except:
                            body = {}

                        result["success"] = (
                            resp.status_code == 200 and body.get("status") == "success"
                        )

                        result["content"] = body
                        if body.get("ground_category"):
                            calculated_harmonized_value = body.get(
                                "ground_category"
                            ).get("harmonized_value")
                            control_harmonized_value = location[2]
                            if control_harmonized_value == calculated_harmonized_value:

                                result["control_harmonized_values"] = "success"
                                result["control_harmonized_values_message"] = (
                                    "Harmonized value matches control value."
                                )
                            else:
                                result["control_harmonized_values"] = "error"
                                result["control_harmonized_values_message"] = (
                                    f"❌ Harmonized value mismatch at coordinates ({x},{y}): "
                                    f"expected '{control_harmonized_value}', got '{calculated_harmonized_value}'"
                                )

                    except Exception as e:
                        result["error"] = str(e)

                    await ws.send_json(result)
                    await asyncio.sleep(0.05)

        await ws.send_json({"event": "end"})

    except WebSocketDisconnect:
        pass

    except Exception as e:
        await ws.send_json({"error": f"Server error: {e}"})
        await ws.close()
