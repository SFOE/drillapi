from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request, HTTPException, status

# Limiter
limiter = Limiter(key_func=get_remote_address)


# Rate limit handler
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded",
    )


# Example IP verification dependency
async def verify_ip(request: Request):
    # Implement IP verification here
    # raise HTTPException if not allowed
    pass
