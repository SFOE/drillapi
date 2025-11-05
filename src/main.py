from typing import Annotated

from fastapi import FastAPI, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from settings_values import cantons, globals

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)


# start the app
app = FastAPI()

# Define allowed origins
origins = [
    "http://localhost:5173",      # local dev (Vite)
    "https://app.example.com"     # production Vue app
]

# Only allow GET
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # which domains are allowed
    allow_credentials=True,
    allow_methods=["GET"],        # ONLY allow GET
    allow_headers=["*"],          # allow all headers
)

# Register exception handler for rate limit errors
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/v1/{coord_x}/{coord_y}")
@limiter.limit(globals.RATE_LIMIT)
async def get_drill_category(
    request: Request,
    coord_x: Annotated[
        float,
        Path(title="X coordinate of the location in EPSG:2056", gt=2400000, le=2900000),
    ],
    coord_y: Annotated[
        float,
        Path(title="Y coordinate of the location in EPSG:2056", gt=1070000, le=1300000),
    ],
):

    for item in cantons.CANTONS_LIST:
        print(item)

    # TODO: Implement logic to determine drill category based on coordinates

    return {"coord_x": coord_x, "coord_y": coord_y, "drill_category": "Not Implemented"}


"""Display list of cantons available in the API."""


@app.get("/v1/cantons")
@limiter.limit(globals.RATE_LIMIT)
async def get_drill_category(
    request: Request,
):
    return cantons.CANTONS_LIST
