from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from settings_values import cantons
from src.services.security import verify_ip
import httpx, json, urllib.parse

router = APIRouter()


@router.get(
    "/checker/", response_class=StreamingResponse, dependencies=[Depends(verify_ip)]
)
async def checker(request: Request):
    config = cantons.CANTONS["cantons_configurations"]

    async def generator():
        yield "<html><head><style>pre{white-space:pre-wrap;} .error-box{width:80vw;margin:10px auto;background:#f8d7da;padding:10px;overflow-x:auto;font-size:0.9em;} summary{cursor:pointer;font-weight:bold;}</style></head><body><pre>"
        yield "<h2>Service Availability Checker</h2>"

        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for canton, data in config.items():
                yield f"<strong>Checking service for {canton}</strong>\n"
                for location in data["exampleLocation"]:
                    url = f"/v1/drill-category/{location[0]}/{location[1]}"
                    yield f" - Checking {url} ... "
                    try:
                        resp = await client.get(url, timeout=60.0)
                        if resp.status_code == 200:
                            json_content = resp.json()
                            yield f"""
<details class="error-box" style="background:#d4edda;border:1px solid #c3e6cb;">
<summary>✅ Success - Click to view details</summary>
<pre>{json.dumps(json_content, indent=2)}</pre>
</details>
"""
                        else:
                            content = (
                                resp.json()
                                if resp.headers.get("content-type")
                                == "application/json"
                                else resp.text
                            )
                            yield f"""
<details class="error-box">
<summary>❌ Failed (HTTP {resp.status_code})</summary>
<pre>{content}</pre>
</details>
"""
                    except Exception as e:
                        yield f"<details class='error-box'><summary>❌ Request Error</summary>{e}</details>"
                yield "\n"

        yield "<strong>All checks completed.</strong></pre></body></html>"

    return StreamingResponse(generator(), media_type="text/html")
