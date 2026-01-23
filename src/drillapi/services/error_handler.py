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
    import traceback
    import logging
    from fastapi import HTTPException
    from ..config import settings

    logger = logging.getLogger(func.__module__)

    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise  # Let FastAPI handle HTTPExceptions
        except Exception as e:
            tb = traceback.format_exc()
            logger.error("Unhandled error in %s:\n%s", func.__name__, tb)

            if settings.ENVIRONMENT.upper() == "DEV":
                raise  # Full traceback in dev
            else:
                # Optionally include the short exception message
                detail_msg = str(e) if str(e) else "An internal error occurred."
                raise HTTPException(status_code=500, detail=detail_msg)

    return wrapper
