from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from settings_values import cantons
from src.services.security import verify_ip
import httpx, json, asyncio

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")


@router.get("/checker/", response_class=HTMLResponse, dependencies=[Depends(verify_ip)])
async def checker_page(request: Request):
    """
    Renders the main Service Availability Checker page.

    This page loads the shell HTML (`checker_stream.html`) and starts the
    streaming process via the `/checker/stream` endpoint using SSE (Server-Sent Events).

    - **request**: FastAPI Request object
    - Returns: HTML page
    """
    return templates.TemplateResponse("checker_stream.html", {"request": request})


@router.get("/checker/stream", dependencies=[Depends(verify_ip)])
async def checker_stream():
    """
    Streams service availability check results as Server-Sent Events (SSE).

    Acess is restricted to whitelisted IP addresses

    For each configured canton and example location:
    - Calls `/v1/drill-category/{coord_x}/{coord_y}`
    - Returns JSON data for each check:
        - `canton`: Canton code
        - `url`: Service URL checked
        - `status`: HTTP status code
        - `success`: True/False based on service response
        - `content`: JSON content of the response
        - `error`: Error message if request failed

    Sends an `end` event when all checks are completed.
    """
    config = cantons.CANTONS["cantons_configurations"]

    async def event_generator():
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for canton, data in config.items():
                for location in data["exampleLocation"]:
                    url = f"/v1/drill-category/{location[0]}/{location[1]}"
                    result = {"canton": canton, "url": url}

                    try:
                        resp = await client.get(url, timeout=60.0)
                        result["status"] = resp.status_code
                        print("------------------")
                        print(resp.json().get("status"))
                        if (
                            resp.status_code == 200
                            and resp.json().get("status") == "success"
                        ):
                            result["success"] = True
                        else:
                            result["success"] = False

                        result["content"] = json.dumps(resp.json(), indent=2)
                    except Exception as e:
                        result["error"] = str(e)

                    # Send each result as JSON
                    yield f"data: {json.dumps(result)}\n\n"
                    await asyncio.sleep(0.1)

        yield "event: end\ndata: done\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
