from fastapi import APIRouter, Request, Path, HTTPException
from drillapi.cantons_configuration import cantons
from ..services.security import limiter
from ..config import settings

router = APIRouter()


def filter_active_cantons(cantons):
    """
    return a new dict containing only those cantons whose 'active' key is True.
    """
    return {key: value for key, value in cantons.items() if value.get("active") is True}


def get_cantons_data():
    return cantons.CANTONS["cantons_configurations"]


@router.get(
    "/v1/cantons",
    summary="Get all cantons",
    response_description="Dictionary of all cantons with their configurations",
)
@limiter.limit(settings.RATE_LIMIT)
async def get_all_cantons(request: Request):
    """
    Retrieve all cantons configurations.

    Returns a dictionary where each key is a canton code (e.g., 'ZH', 'GE')
    and each value is the configuration for that canton.

    **Rate limit:** Respects global `RATE_LIMIT` setting.

    **Returns:**
    - `dict[str, dict]`: All cantons configurations
    """
    return get_cantons_data()


@router.get(
    "/v1/cantons/{code}",
    summary="Get a canton by code",
    response_description="Configuration for a specific canton",
)
@limiter.limit(settings.RATE_LIMIT)
async def get_canton_by_code(
    request: Request, code: str = Path(..., min_length=2, max_length=2)
):
    """
    Retrieve the configuration for a single canton by its 2-letter code.

    **Path Parameters:**
    - `code` (str): The 2-letter canton code (e.g., 'ZH', 'GE')

    **Returns:**
    - `dict[str, dict]`: Canton code as key and its configuration as value

    **Raises:**
    - `HTTPException 404`: If the canton code does not exist
    """
    code = code.upper()
    data = get_cantons_data()
    if code not in data:
        raise HTTPException(404, f"Canton '{code}' not found")
    return {code: data[code]}


@router.get(
    "/v1/avalaible-cantons",
    summary="Get canton that are configured and available",
    response_description="List of available canton codes",
)
@limiter.limit(settings.RATE_LIMIT)
async def get_available_cantons(request: Request):
    """
    Retrieve the available cantons code for which a working geoservice exists and is configured.


    **Returns:**
    - `list[str]`: Canton code as list

    """

    data = list(filter_active_cantons(get_cantons_data()).keys())

    return data
