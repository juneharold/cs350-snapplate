import io
import time

import pytest
from PIL import Image

from tests.conftest import auth_headers

KAIST = {"lat": 36.3504, "lng": 127.3845}


def _jpeg() -> bytes:
    img = Image.new("RGB", (400, 300), (180, 100, 70))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _seed_entries(client, headers, n: int):
    rests = client.get(
        "/v1/restaurants/nearby", params={**KAIST, "radius_m": 1500, "limit": 15}, headers=headers
    ).json()["response"]["items"]
    assert rests, "no restaurants to seed against"
    seeded = 0
    for i in range(n):
        # Cycle restaurants if fewer than n exist (a user logs multiple visits).
        rest = rests[i % len(rests)]
        mid = client.post(
            "/v1/media/upload",
            files={"files": (f"s{i}.jpg", _jpeg(), "image/jpeg")},
            headers=headers,
        ).json()["response"]["uploads"][0]["id"]
        month, day = (i % 5) + 1, (i % 27) + 1  # always-valid past dates
        did = client.post(
            "/v1/drafts",
            json={
                "media_ids": [mid],
                "restaurant_id": rest["id"],
                "captured_at": f"2026-{month:02d}-{day:02d}T12:30:00Z",
            },
            headers=headers,
        ).json()["response"]["id"]
        if (
            client.post(
                f"/v1/drafts/{did}/finalize",
                json={"note": f"Visit {i}.", "rating": 3.5 + (i % 3) * 0.5},
                headers=headers,
            ).status_code
            == 201
        ):
            seeded += 1
    return seeded


def _refresh_taste_and_wait(client, headers) -> dict:
    queued = client.post("/v1/taste/refresh", headers=headers)
    assert queued.status_code == 202
    assert queued.json()["response"]["job_id"]
    for _ in range(30):
        response = client.get("/v1/taste/profile", headers=headers)
        if response.status_code == 200:
            profile = response.json()["response"]
            if profile["has_enough_data"]:
                return profile
        time.sleep(0.5)
    raise AssertionError("taste profile refresh did not complete")


def _recommendations_and_wait(client, headers) -> dict:
    last_status = None
    for _ in range(30):
        response = client.get("/v1/restaurants/recommended", params=KAIST, headers=headers)
        last_status = response.status_code
        if response.status_code == 200:
            body = response.json()["response"]
            if body["has_enough_data"] and body["items"]:
                return body
        time.sleep(0.5)
    raise AssertionError(f"recommendations did not become ready; last status={last_status}")


@pytest.fixture(scope="module")
def seeded_headers(server):
    import httpx

    with httpx.Client(base_url=server, timeout=30) as c:
        h = auth_headers(c, "t-taste@snapplate.app")
        n = _seed_entries(c, h, 12)
        assert n >= 10, f"only seeded {n}"
        _refresh_taste_and_wait(c, h)
    return h


def test_recommendations(server, seeded_headers):
    import httpx

    with httpx.Client(base_url=server, timeout=30) as c:
        body = _recommendations_and_wait(c, seeded_headers)
        assert body["has_enough_data"] is True
        assert len(body["items"]) > 0
        assert "reason" in body["items"][0]


def test_taste_profile(server, seeded_headers):
    import httpx

    with httpx.Client(base_url=server, timeout=30) as c:
        prof = _refresh_taste_and_wait(c, seeded_headers)
        assert prof["has_enough_data"] is True
        assert "type" in prof and prof["type"]["label"]
        me = c.get("/v1/me", headers=seeded_headers).json()["response"]
        assert me["taste_type"] is not None


def test_app_info(server):
    import httpx

    with httpx.Client(base_url=server, timeout=30) as c:
        h = auth_headers(c, "t-appinfo@snapplate.app")
        r = c.get("/v1/app-info", headers=h)
        assert r.status_code == 200
        assert "version" in r.json()["response"]
