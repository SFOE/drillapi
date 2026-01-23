from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from .routes import drill_category, cantons, checker
from .services.security import limiter, rate_limit_handler, RateLimitExceeded
from .config import settings
import logging

LOG_LEVEL = logging.DEBUG if settings.ENVIRONMENT.upper() == "DEV" else logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(LOG_LEVEL)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Routers
app.include_router(drill_category.router)
app.include_router(cantons.router)
app.include_router(checker.router)

# Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "docs_url": "/docs", "redoc_url": "/redoc"}
    )
