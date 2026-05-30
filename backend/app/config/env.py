from __future__ import annotations

from enum import StrEnum, auto
from os import environ
from typing import Literal, overload


class Env(StrEnum):
    """Parent process env vars are inherited by child processes and threads.
    Cf. https://stackoverflow.com/a/24664312

    Lean config: a StrEnum that loads `.env` and seeds defaults. No pydantic-settings,
    no EnvType tri-state (we have one deploy target in v1). Add EnvType only when a real
    second environment (staging) needs *different behavior*, not before.
    """

    # Postgres
    DB_USER = auto()
    DB_PASSWORD = auto()
    DB_HOST = auto()
    DB_NAME = auto()
    DB_PORT = auto()

    # Object storage (MinIO locally; S3_ENDPOINT is the only line that changes for R2/S3)
    S3_ENDPOINT = auto()
    S3_ACCESS_KEY = auto()
    S3_SECRET_KEY = auto()
    S3_BUCKET = auto()
    S3_REGION = auto()

    # Kakao Local REST (restaurant data)
    KAKAO_REST_API_KEY = auto()

    # Auth (self-host: we issue our own JWTs)
    JWT_SECRET_KEY = auto()
    JWT_EXPIRATION_HOURS = auto()

    # Email provider for magic links
    SMTP_URL = auto()

    @staticmethod
    def load_defaults():
        from dotenv import load_dotenv

        load_dotenv(verbose=True)

        variables = {
            Env.DB_USER: Env.raw_get("DB_USER") or "snapplate",
            Env.DB_PASSWORD: Env.raw_get("DB_PASSWORD") or "snapplate",
            Env.DB_HOST: Env.raw_get("DB_HOST") or "localhost",
            Env.DB_NAME: Env.raw_get("DB_NAME") or "snapplate",
            Env.DB_PORT: Env.raw_get("DB_PORT") or "5432",
            Env.S3_ENDPOINT: Env.raw_get("S3_ENDPOINT") or "http://localhost:9000",
            Env.S3_ACCESS_KEY: Env.raw_get("S3_ACCESS_KEY") or "localdev",
            Env.S3_SECRET_KEY: Env.raw_get("S3_SECRET_KEY") or "localdev123",
            Env.S3_BUCKET: Env.raw_get("S3_BUCKET") or "media",
            Env.S3_REGION: Env.raw_get("S3_REGION") or "us-east-1",
            Env.KAKAO_REST_API_KEY: Env.raw_get("KAKAO_REST_API_KEY") or "",
            Env.JWT_SECRET_KEY: Env.raw_get("JWT_SECRET_KEY") or "dev-only-change-me",
            Env.JWT_EXPIRATION_HOURS: Env.raw_get("JWT_EXPIRATION_HOURS") or "720",
            Env.SMTP_URL: Env.raw_get("SMTP_URL") or "",
        }
        for key, value in variables.items():
            Env.set(key, value)

    @staticmethod
    def set(key: Env, value: str):
        environ[key] = value

    @staticmethod
    def get(key: Env):
        return environ[key]

    @overload
    @staticmethod
    def raw_get(key: str, raise_if_none: Literal[True]) -> str: ...

    @overload
    @staticmethod
    def raw_get(key: str, raise_if_none: Literal[False] = ...) -> str | None: ...

    @overload
    @staticmethod
    def raw_get(key: str, raise_if_none: bool = ...) -> str | None: ...

    @staticmethod
    def raw_get(key: str, raise_if_none: bool = False):
        value = environ.get(key, None)
        if (value is None) and raise_if_none:
            raise KeyError(f"Environment variable `{key}` does not exist.")
        return value


def db_dsn() -> str:
    """Async SQLAlchemy DSN. Single source of truth, shared by lifespan and Alembic."""
    return (
        f"postgresql+asyncpg://{Env.get(Env.DB_USER)}:{Env.get(Env.DB_PASSWORD)}"
        f"@{Env.get(Env.DB_HOST)}:{Env.get(Env.DB_PORT)}/{Env.get(Env.DB_NAME)}"
    )
