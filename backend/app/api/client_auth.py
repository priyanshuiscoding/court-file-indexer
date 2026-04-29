from fastapi import Header, HTTPException

from app.core.config import get_settings

settings = get_settings()


def verify_client_api_key(x_api_key: str | None = Header(default=None)):
    if not settings.ENABLE_CLIENT_API_AUTH:
        return True

    if not settings.CLIENT_API_KEY:
        raise HTTPException(status_code=500, detail="Client API key not configured")

    if not x_api_key or x_api_key != settings.CLIENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return True
