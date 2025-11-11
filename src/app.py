from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from src.routes import drill_category, cantons, checker
from src.services.security import limiter, rate_limit_handler, RateLimitExceeded

app = FastAPI()

# Routers
app.include_router(drill_category.router)
app.include_router(cantons.router)
app.include_router(checker.router)

# Templates
templates = Jinja2Templates(directory="src/templates")

# Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
