from fastapi import APIRouter, Request, Path, HTTPException
from settings_values import cantons, globals
from src.services.security import limiter

router = APIRouter()


def get_cantons_data():
    return cantons.CANTONS["cantons_configurations"]


@router.get("/v1/cantons")
@limiter.limit(globals.RATE_LIMIT)
async def get_all_cantons(request: Request):
    return get_cantons_data()


@router.get("/v1/cantons/{code}")
@limiter.limit(globals.RATE_LIMIT)
async def get_canton_by_code(
    request: Request, code: str = Path(..., min_length=2, max_length=2)
):
    code = code.upper()
    data = get_cantons_data()
    if code not in data:
        raise HTTPException(404, f"Canton '{code}' not found")
    return {code: data[code]}
