import functools
import traceback
import logging
from fastapi import HTTPException
from ..config import settings

logger = logging.getLogger(__name__)


def handle_errors(func):
    """
    Decorator to catch exceptions in endpoints and async sub-functions.
    Logs full traceback in DEV, returns minimal message in PROD.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Let FastAPI handle HTTPExceptions normally
            raise
        except Exception as e:
            # Full traceback
            tb = traceback.format_exc()
            logger.error("Unhandled error in %s:\n%s", func.__name__, tb)

            if settings.ENVIRONMENT.upper() == "DEV":
                # Reraise exception to see full traceback in FastAPI
                raise
            else:
                # In PROD, return clean error
                raise HTTPException(
                    status_code=500,
                    detail="An internal error occurred. Please contact support.",
                )

    return wrapper
