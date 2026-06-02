from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum

import httpx


class HttpConfig(Enum):
    NUM_CONN_POOL = 100
    EXPIRE_CONN_POOL = 60

    TIMEOUT_TOTAL = 5.0
    TIMEOUT_CONNECT = 2.0


@asynccontextmanager
async def create_httpx_client() -> AsyncIterator[httpx.AsyncClient]:
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            timeout=HttpConfig.TIMEOUT_TOTAL.value,
            connect=HttpConfig.TIMEOUT_CONNECT.value,
        ),
        limits=httpx.Limits(
            max_connections=HttpConfig.NUM_CONN_POOL.value,
            max_keepalive_connections=HttpConfig.NUM_CONN_POOL.value,
            keepalive_expiry=HttpConfig.EXPIRE_CONN_POOL.value,
        ),
    )
    try:
        yield client
    finally:
        await client.aclose()
