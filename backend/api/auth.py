"""
RevenueOS API Authentication & Security Middleware
===================================================
Provides API-key header and query parameter verification with
environment-configurable enforcement.
"""

from __future__ import annotations

import os
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery

API_KEY_HEADER = APIKeyHeader(name="X-RevenueOS-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)


def get_expected_api_key() -> Optional[str]:
    """Retrieve configured API key from environment variable."""
    key = os.getenv("REVENUEOS_API_KEY", "").strip()
    return key or None


async def verify_api_key(
    header_key: Optional[str] = Security(API_KEY_HEADER),
    query_key: Optional[str] = Security(API_KEY_QUERY),
) -> Optional[str]:
    """
    Validates API key from either 'X-RevenueOS-API-Key' header or '?api_key=' query param.
    If REVENUEOS_API_KEY is not configured in the environment, requests are permitted.
    If REVENUEOS_API_KEY is configured, invalid or missing keys return HTTP 403 Forbidden.
    """
    expected = get_expected_api_key()
    if not expected:
        # Development / local mode: no key configured, permit access
        return None

    provided_key = header_key or query_key
    if not provided_key or provided_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Provide a valid 'X-RevenueOS-API-Key' header or '?api_key=' query parameter.",
        )

    return provided_key
