from __future__ import annotations

import secrets

_ID_BYTES = 8


def make_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(_ID_BYTES)}"


def user_id() -> str:
    return make_id("u")


def restaurant_id() -> str:
    return make_id("r")


def media_id() -> str:
    return make_id("m")


def draft_id() -> str:
    return make_id("d")


def entry_id() -> str:
    return make_id("e")


def bookmark_id() -> str:
    return make_id("b")


def push_token_id() -> str:
    return make_id("pt")


def taste_job_id() -> str:
    return make_id("tj")
