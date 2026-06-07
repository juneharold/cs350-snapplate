import io
from urllib.parse import urlparse

from PIL import Image

from tests.conftest import auth_headers


def _jpeg() -> bytes:
    img = Image.new("RGB", (100, 100), (200, 90, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_me_returns_stats(client):
    h = auth_headers(client, "t-me@snapplate.app")
    r = client.get("/v1/me", headers=h)
    assert r.status_code == 200
    me = r.json()["response"]
    assert set(me["stats"]) == {"entries_count", "places_count", "bookmarks_count", "avg_rating"}


def test_patch_me_nickname(client):
    h = auth_headers(client, "t-nick@snapplate.app")
    r = client.patch("/v1/me", json={"nickname": "Chef Jin"}, headers=h)
    assert r.status_code == 200
    assert r.json()["response"]["nickname"] == "Chef Jin"


def test_patch_me_nickname_too_long(client):
    h = auth_headers(client, "t-long@snapplate.app")
    r = client.patch("/v1/me", json={"nickname": "x" * 40}, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "nickname_too_long"


def test_settings_get_and_patch(client):
    h = auth_headers(client, "t-settings@snapplate.app")
    assert client.get("/v1/settings", headers=h).status_code == 200
    r = client.patch(
        "/v1/settings",
        json={"notifications": {"weekly_picks": True}, "appearance": "dark"},
        headers=h,
    )
    s = r.json()["response"]
    assert s["notifications"]["weekly_picks"] is True
    assert s["appearance"] == "dark"


def test_settings_bad_appearance(client):
    h = auth_headers(client, "t-appearance@snapplate.app")
    r = client.patch("/v1/settings", json={"appearance": "neon"}, headers=h)
    assert r.status_code == 422


def test_upload_avatar_success(client):
    h = auth_headers(client, "t-avatar@snapplate.app")

    # 1. Upload avatar
    r = client.post(
        "/v1/me/avatar",
        files={"file": ("avatar.jpg", _jpeg(), "image/jpeg")},
        headers=h,
    )
    assert r.status_code == 200
    res = r.json()["response"]
    assert "profile_image_url" in res
    assert "http://localhost:9000/media/avatars/" in res["profile_image_url"]

    # 2. Check /me endpoint returns the signed profile image url. Presigned URLs
    #    carry a per-call signature/expiry in the query string, so compare only
    #    the object path rather than string-equating two independent signings.
    me_res = client.get("/v1/me", headers=h)
    assert me_res.status_code == 200
    me_data = me_res.json()["response"]
    assert urlparse(me_data["profile_image_url"]).path == urlparse(res["profile_image_url"]).path


def test_upload_avatar_invalid_type(client):
    h = auth_headers(client, "t-avatar-bad@snapplate.app")

    r = client.post(
        "/v1/me/avatar",
        files={"file": ("avatar.txt", b"not-an-image", "text/plain")},
        headers=h,
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unsupported_format"


def test_upload_avatar_rejects_fake_image(client):
    # Bytes that claim to be a JPEG but aren't a decodable image must be
    # rejected before anything is written to S3.
    h = auth_headers(client, "t-avatar-fake@snapplate.app")
    r = client.post(
        "/v1/me/avatar",
        files={"file": ("avatar.jpg", b"not-really-a-jpeg", "image/jpeg")},
        headers=h,
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unsupported_format"
