from __future__ import annotations

from fastapi import APIRouter, Response

api = APIRouter()


@api.get("/health", include_in_schema=False)
async def health() -> Response:
    return Response(status_code=200)


# Mounted under /v1 in main.py.
misc = APIRouter()


@misc.get("/app-info")
async def app_info() -> dict:
    """Static version + legal/contact (satisfies REQ-4.10-003/004/005). No DB."""
    return {
        "code": 0,
        "success": True,
        "message": "success",
        "response": {
            "version": "1.0.0",
            "terms_url": "https://snapplate.app/terms",
            "privacy_url": "https://snapplate.app/privacy",
            "contact_url": "https://snapplate.app/contact",
        },
    }
