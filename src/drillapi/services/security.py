from fastapi import Request, HTTPException, status, Depends
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from ..config import settings  # assuming ALLOWED_IPS is in your Settings

# Limiter
limiter = Limiter(key_func=get_remote_address)


# Rate limit handler
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded",
    )
