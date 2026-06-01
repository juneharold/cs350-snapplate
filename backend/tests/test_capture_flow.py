import io

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
    d = client.post("/v1/drafts", json={"media_ids": [mid], **KAIST}, headers=headers).json()["response"]
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


def test_finalize_requires_note(client, headers):
    mid = client.post(
        "/v1/media/upload", files={"files": ("p.jpg", _jpeg(), "image/jpeg")}, headers=headers
    ).json()["response"]["uploads"][0]["id"]
    did = client.post("/v1/drafts", json={"media_ids": [mid], **KAIST}, headers=headers).json()["response"]["id"]
    r = client.post(f"/v1/drafts/{did}/finalize", json={"note": ""}, headers=headers)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "note_required"
    # draft still there (atomicity)
    assert client.get(f"/v1/drafts/{did}", headers=headers).status_code == 200
