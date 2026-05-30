from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.config.env import Env


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    # Skeleton lifespan: load env and boot. The data-layer clients (DB engine,
    # MinIO/S3) are wired in once the data layer exists.
    Env.load_defaults()
    yield
