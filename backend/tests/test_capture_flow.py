import io
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image

from tests.conftest import auth_headers

KAIST = {"lat": 36.3504, "lng": 127.3845}


def _jpeg() -> bytes:
    img = Image.new("RGB", (800, 600), (200, 90, 60))
    exif = img.getexif()
    exif[306] = "2026:05:24 12:43:00"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


@pytest.fixture
def headers(client):
    return auth_headers(client, "t-capture@snapplate.app")


def test_media_upload(client, headers):
    r = client.post(
        "/v1/media/upload",
        files={"files": ("p.jpg", _jpeg(), "image/jpeg")},
        headers=headers,
    )
    assert r.status_code == 200
    up = r.json()["response"]["uploads"][0]
    assert up["url"] and up["thumbnail_url"]
    assert up["exif"]["has_timestamp"] is True


def test_full_capture_to_diary(client, headers):
    # upload
    mid = client.post(
        "/v1/media/upload", files={"files": ("p.jpg", _jpeg(), "image/jpeg")}, headers=headers
    ).json()["response"]["uploads"][0]["id"]
    # draft with GPS → restaurant suggested
    d = client.post("/v1/drafts", json={"media_ids": [mid], **KAIST}, headers=headers).json()[
        "response"
    ]
    assert d["restaurant"] is not None
    assert d["restaurant_suggested"] is True
    # finalize
    r = client.post(
        f"/v1/drafts/{d['id']}/finalize",
        json={"note": "Great meal, tender.", "rating": 4.5},
        headers=headers,
    )
    assert r.status_code == 201
    eid = r.json()["response"]["entry_id"]
    # draft gone
    assert client.get(f"/v1/drafts/{d['id']}", headers=headers).status_code == 404
    # entry in diary
    entries = client.get("/v1/entries", headers=headers).json()["response"]
    assert entries["total"] >= 1
    det = client.get(f"/v1/entries/{eid}", headers=headers).json()["response"]
    assert det["meal_period"]
    assert "user_visit_history" in det


def test_capture_allows_small_clock_skew(client, headers):
    mid = client.post(
        "/v1/media/upload", files={"files": ("p.jpg", _jpeg(), "image/jpeg")}, headers=headers
    ).json()["response"]["uploads"][0]["id"]
    captured_at = (datetime.now(UTC) + timedelta(seconds=30)).isoformat()

    d = client.post(
        "/v1/drafts",
        json={"media_ids": [mid], "captured_at": captured_at, **KAIST},
        headers=headers,
    )

    assert d.status_code == 201
    draft = d.json()["response"]
    r = client.post(
        f"/v1/drafts/{draft['id']}/finalize",
        json={"note": "Captured from a slightly fast phone clock."},
        headers=headers,
    )
    assert r.status_code == 201


def test_finalize_requires_note(client, headers):
    mid = client.post(
        "/v1/media/upload", files={"files": ("p.jpg", _jpeg(), "image/jpeg")}, headers=headers
    ).json()["response"]["uploads"][0]["id"]
    did = client.post("/v1/drafts", json={"media_ids": [mid], **KAIST}, headers=headers).json()[
        "response"
    ]["id"]
    r = client.post(f"/v1/drafts/{did}/finalize", json={"note": ""}, headers=headers)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "note_required"
    # draft still there (atomicity)
    assert client.get(f"/v1/drafts/{did}", headers=headers).status_code == 200


def test_draft_cannot_link_another_users_media(client):
    """A draft may only link media the caller owns (REQ-SEC-004 / REQ-SEC-009).

    Otherwise a guessed media id would let one user attach (and get a signed
    URL for) another user's photo.
    """
    owner = auth_headers(client, "t-media-owner@snapplate.app")
    attacker = auth_headers(client, "t-media-attacker@snapplate.app")

    victim_mid = client.post(
        "/v1/media/upload", files={"files": ("p.jpg", _jpeg(), "image/jpeg")}, headers=owner
    ).json()["response"]["uploads"][0]["id"]

    # Attacker tries to point their own draft at the victim's media.
    r = client.post("/v1/drafts", json={"media_ids": [victim_mid], **KAIST}, headers=attacker)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "media_not_found"


def test_deleted_account_token_is_rejected(client):
    """A valid JWT for a soft-deleted account must not access protected
    endpoints (REQ-4.1-008). The token is still signature-valid and unexpired."""
    h = auth_headers(client, "t-deleted@snapplate.app")
    # works before deletion
    assert client.get("/v1/me", headers=h).status_code == 200
    # soft-delete the account (sets deleted_at)
    d = client.request(
        "DELETE", "/v1/account", json={"confirm_email": "t-deleted@snapplate.app"}, headers=h
    )
    assert d.status_code in (200, 204)
    # same (still unexpired) token must now be rejected
    assert client.get("/v1/me", headers=h).status_code == 401
