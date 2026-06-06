import pytest

from tests.conftest import auth_headers

KAIST = {"lat": 36.3504, "lng": 127.3845}


@pytest.fixture
def warm_restaurant(client):
    """Ensure the cache has restaurants; return one restaurant id."""
    h = auth_headers(client, "t-rest-seed@snapplate.app")
    r = client.get("/v1/restaurants/nearby", params={**KAIST, "radius_m": 1000, "limit": 10}, headers=h)
    items = r.json()["response"]["items"]
    assert items, "Kakao should return restaurants near KAIST"
    return items[0]["id"]


def test_nearby_returns_restaurants(client):
    h = auth_headers(client, "t-nearby@snapplate.app")
    r = client.get("/v1/restaurants/nearby", params={**KAIST, "radius_m": 1000, "limit": 5}, headers=h)
    assert r.status_code == 200
    items = r.json()["response"]["items"]
    assert len(items) > 0
    first = items[0]
    # contract-required fields
    for f in ("thumbnail_tone", "thumbnail_label", "neighborhood", "kakao_id", "distance_m"):
        assert f in first


def test_nearby_respects_radius(client):
    """Every returned restaurant must be within the requested radius_m. The
    cache is not geo-bounded, so a missing filter would leak far-away places
    (REQ-4.2-007)."""
    h = auth_headers(client, "t-radius@snapplate.app")
    radius = 800
    r = client.get(
        "/v1/restaurants/nearby",
        params={**KAIST, "radius_m": radius, "limit": 20},
        headers=h,
    )
    assert r.status_code == 200
    items = r.json()["response"]["items"]
    assert all(i["distance_m"] <= radius for i in items)


def test_detail(client, warm_restaurant):
    h = auth_headers(client, "t-detail@snapplate.app")
    r = client.get(f"/v1/restaurants/{warm_restaurant}", headers=h)
    assert r.status_code == 200
    assert r.json()["response"]["kakao_place_url"].startswith("https://place.map.kakao.com/")


def test_detail_404(client):
    h = auth_headers(client, "t-404@snapplate.app")
    r = client.get("/v1/restaurants/r_nonexistent", headers=h)
    assert r.status_code == 404


def test_bookmark_add_dup_list_delete(client, warm_restaurant):
    h = auth_headers(client, "t-bm@snapplate.app")
    rid = warm_restaurant
    assert client.post("/v1/bookmarks", json={"restaurant_id": rid}, headers=h).status_code == 201
    assert client.post("/v1/bookmarks", json={"restaurant_id": rid}, headers=h).status_code == 409
    lst = client.get("/v1/bookmarks", headers=h).json()["response"]
    assert lst["total"] >= 1
    assert lst["items"][0]["restaurant"]["is_bookmarked"] is True
    assert client.delete(f"/v1/bookmarks/{rid}", headers=h).status_code == 204
    assert client.delete(f"/v1/bookmarks/{rid}", headers=h).status_code == 404
