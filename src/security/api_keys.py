from typing import Optional

from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

from ..config import security_settings
from ..core.logging import logger


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In a real application, API keys would be stored securely (e.g., database)
# and hashed. For demonstration, we use a hardcoded key.
API_KEYS = {
    "service-to-service-key": security_settings.SECRET_KEY # Using SECRET_KEY as a placeholder API key
}

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key is None:
        logger.warning("API Key missing")
        raise HTTPException(status_code=401, detail="API Key missing")
    if api_key not in API_KEYS.values(): # In production, hash and compare
        logger.warning("Invalid API Key provided")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

async def get_api_key_name(api_key: str = Security(api_key_header)) -> Optional[str]:
    for name, key in API_KEYS.items():
        if key == api_key:
            return name
    return None
