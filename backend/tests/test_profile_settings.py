from tests.conftest import auth_headers


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
