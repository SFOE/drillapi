from fastapi import Request, HTTPException, status, Depends
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from src.config import settings  # assuming ALLOWED_IPS is in your Settings

# Limiter
limiter = Limiter(key_func=get_remote_address)


# Rate limit handler
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded",
    )


# IP verification dependency
async def verify_ip(request: Request):
    """
    Verifies that the client IP is allowed.
    Raises HTTP 403 if not allowed.
    """
    # Get the client IP (works behind proxies if you configure X-Forwarded-For)
    client_ip = request.client.host
    # Optional: check for headers if behind a proxy/load balancer
    # client_ip = request.headers.get("X-Forwarded-For", client_ip).split(",")[0].strip()

    if client_ip not in settings.ALLOWED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP {client_ip} is not allowed",
        )

    # Optionally return the IP if downstream code needs it
    return client_ip
