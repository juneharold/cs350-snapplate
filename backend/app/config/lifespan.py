from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, TypedDict, cast

import aioboto3
import httpx
from fastapi import FastAPI, Request
from openai import OpenAI
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.env import Env, db_dsn
from app.config.http_client import create_httpx_client
from app.config.logger import create_logger
from app.services.algorithm.providers import DeterministicProvider, OpenAIProvider, ProfileProvider
from app.services.algorithm.service import AlgorithmService


@dataclass
class InternalContext:
    """Long-lived, app-lifetime clients. One per process."""

    db_engine: AsyncEngine
    db_sessionmaker: async_sessionmaker[AsyncSession]
    http_client: httpx.AsyncClient
    s3: aioboto3.Session
    algorithm_service: AlgorithmService


@dataclass
class Context:
    """Per-request context: shared clients + a fresh db_session."""

    db_session: AsyncSession
    http_client: httpx.AsyncClient
    s3: aioboto3.Session
    algorithm_service: AlgorithmService


class State(TypedDict):
    context: InternalContext


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:  # noqa: ARG001
    Env.load_defaults()
    algorithm_service = AlgorithmService(_build_profile_provider())

    db_engine = create_async_engine(db_dsn(), echo=False, pool_pre_ping=True)
    # expire_on_commit=False so ORM objects stay usable after commit (serialization).
    db_sessionmaker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with create_httpx_client() as http_client:
        s3 = aioboto3.Session()

        # Create the MinIO bucket once if it doesn't exist (dev convenience).
        s3_client = cast(Any, s3.client)(
            "s3",
            endpoint_url=Env.get(Env.S3_ENDPOINT),
            aws_access_key_id=Env.get(Env.S3_ACCESS_KEY),
            aws_secret_access_key=Env.get(Env.S3_SECRET_KEY),
            region_name=Env.get(Env.S3_REGION),
        )
        async with s3_client as client:
            with contextlib.suppress(Exception):
                await client.create_bucket(Bucket=Env.get(Env.S3_BUCKET))

        internal = InternalContext(
            db_engine=db_engine,
            db_sessionmaker=db_sessionmaker,
            http_client=http_client,
            s3=s3,
            algorithm_service=algorithm_service,
        )
        try:
            yield {"context": internal}
        finally:
            await db_engine.dispose()


async def get_context(request: Request) -> AsyncIterator[Context]:
    """FastAPI dependency: a per-request Context with a fresh AsyncSession.

    Mirrors oscre's get_ctx_from_request — opens a session, yields the Context,
    rolls back on error, closes on exit.
    """
    internal: InternalContext = request.state.context
    async with internal.db_sessionmaker() as session:
        try:
            yield Context(
                db_session=session,
                http_client=internal.http_client,
                s3=internal.s3,
                algorithm_service=internal.algorithm_service,
            )
        except Exception:
            await session.rollback()
            raise


def _build_profile_provider() -> ProfileProvider:
    provider = Env.raw_get("ALGORITHM_PROVIDER") or "openai"
    match provider.strip().casefold():
        case "openai":
            api_key = Env.raw_get("OPENAI_API_KEY") or ""
            if not api_key:
                # Fall back to the local, no-network provider instead of failing
                # boot, so taste analysis still works in dev/CI (and demos run
                # without billing). The radar/categories/heatmap still differ
                # per user; only the LLM-authored persona label becomes generic.
                create_logger(__name__).warning(
                    "OPENAI_API_KEY not set; using DeterministicProvider for the algorithm."
                )
                return DeterministicProvider()
            return OpenAIProvider(client=OpenAI(api_key=api_key))
        case "deterministic":
            return DeterministicProvider()
        case _:
            raise RuntimeError(f"unsupported ALGORITHM_PROVIDER: {provider}")
