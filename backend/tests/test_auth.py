import re

from tests.conftest import _LOG, auth_headers


def test_magic_link_and_verify(client):
    r = client.post("/v1/auth/magic-link", json={"email": "t-auth@snapplate.app"})
    assert r.status_code == 200
    assert r.json()["response"]["sent"] is True

    token = re.findall(r"token=([A-Za-z0-9_-]+)", _LOG.read_text())[-1]
    r = client.post("/v1/auth/verify", json={"token": token})
    assert r.status_code == 200
    body = r.json()["response"]
    assert body["access_token"]
    assert body["expires_in"] == 2592000


def test_magic_link_token_is_single_use(client):
    client.post("/v1/auth/magic-link", json={"email": "t-single@snapplate.app"})
    token = re.findall(r"token=([A-Za-z0-9_-]+)", _LOG.read_text())[-1]
    assert client.post("/v1/auth/verify", json={"token": token}).status_code == 200
    r2 = client.post("/v1/auth/verify", json={"token": token})
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "expired_token"


def test_invalid_email(client):
    r = client.post("/v1/auth/magic-link", json={"email": "not-an-email"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_email"


def test_protected_route_requires_auth(client):
    r = client.get("/v1/settings")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_protected_route_with_jwt(client):
    h = auth_headers(client, "t-protected@snapplate.app")
    assert client.get("/v1/settings", headers=h).status_code == 200
