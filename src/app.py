from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from src.routes import drill_category, cantons, checker
from src.services.security import limiter, rate_limit_handler, RateLimitExceeded
from src.config import settings


app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # which domains are allowed
    allow_credentials=True,
    allow_methods=["GET"],  # ONLY allow GET
    allow_headers=["*"],  # allow all headers
)

# Routers
app.include_router(drill_category.router)
app.include_router(cantons.router)
app.include_router(checker.router)

# Templates
templates = Jinja2Templates(directory="src/templates")

# Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
