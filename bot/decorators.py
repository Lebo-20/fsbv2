import asyncio
import random
import logging
from functools import wraps
from .config import MAX_RETRIES, BACKOFF_FACTOR

logger = logging.getLogger("XiaoBot.Decorators")

def retry_backoff(retries=MAX_RETRIES, backoff=BACKOFF_FACTOR):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_err = None
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    wait = backoff ** (i + 1) + (random.randint(0, 1000) / 1000)
                    logger.warning(f"Retry {i+1}/{retries} for {func.__name__} after {wait:.2f}s: {e}")
                    await asyncio.sleep(wait)
            raise last_err
        return wrapper
    return decorator
