from __future__ import annotations

import hashlib

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config.env import Env
from app.config.logger import create_logger
from app.dto.restaurant import KakaoRestaurantData
from app.types.restaurant import FoodTone

logger = create_logger(__name__)

_BASE = "https://dapi.kakao.com/v2/local"
_FOOD_GROUP = "FD6"  # Kakao restaurant category group
_TONES = list(FoodTone)


def _auth_header() -> dict[str, str]:
    return {"Authorization": f"KakaoAK {Env.get(Env.KAKAO_REST_API_KEY)}"}


def _tone_for(seed: str) -> FoodTone:
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return _TONES[h % len(_TONES)]


def _category_label(category_name: str) -> str:
    """Kakao category_name is '음식점 > 카페 > 커피전문점' — take the leaf."""
    parts = [p.strip() for p in category_name.split(">") if p.strip()]
    return parts[-1] if parts else category_name


class KakaoService:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http = http_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _get(self, path: str, params: dict) -> dict:
        resp = await self.http.get(f"{_BASE}/{path}", params=params, headers=_auth_header())
        resp.raise_for_status()
        return resp.json()

    async def keyword_search(
        self, query: str, lat: float | None = None, lng: float | None = None, radius_m: int = 1500
    ) -> list[KakaoRestaurantData]:
        params: dict = {"query": query, "category_group_code": _FOOD_GROUP, "size": 15}
        if lat is not None and lng is not None:
            params.update({"x": lng, "y": lat, "radius": min(radius_m, 20000)})
        data = await self._get("search/keyword.json", params)
        return [self._to_data(d) for d in data.get("documents", [])]

    async def category_search(
        self, lat: float, lng: float, radius_m: int = 1500
    ) -> list[KakaoRestaurantData]:
        params = {
            "category_group_code": _FOOD_GROUP,
            "x": lng,
            "y": lat,
            "radius": min(radius_m, 20000),
            "size": 15,
            "sort": "distance",
        }
        data = await self._get("search/category.json", params)
        return [self._to_data(d) for d in data.get("documents", [])]

    async def neighborhood_for(self, lat: float, lng: float) -> str:
        """coord2regioncode → region_3depth_name (the 'neighborhood')."""
        try:
            data = await self._get("geo/coord2regioncode.json", {"x": lng, "y": lat})
            docs = data.get("documents", [])
            for d in docs:
                if d.get("region_type") == "H" and d.get("region_3depth_name"):
                    return d["region_3depth_name"]
            if docs:
                return docs[0].get("region_3depth_name", "")
        except Exception as e:
            logger.warning(f"coord2regioncode failed: {e}")
        return ""

    @staticmethod
    def _to_data(doc: dict) -> KakaoRestaurantData:
        name = doc.get("place_name", "")
        raw_category = doc.get("category_name", "")
        category = _category_label(raw_category)
        lat = float(doc.get("y", 0.0))
        lng = float(doc.get("x", 0.0))
        return KakaoRestaurantData(
            kakao_id=str(doc.get("id", "")),
            name=name,
            category=category,
            signature_dish=None,
            rating=0.0,
            rating_count=0,
            thumbnail_url=doc.get("place_url"),
            thumbnail_tone=_tone_for(doc.get("id", name)),
            thumbnail_label=name[:24],
            tags=[],
            lat=lat,
            lng=lng,
            neighborhood="",  # filled by neighborhood_for if needed
            address=doc.get("road_address_name") or doc.get("address_name"),
            price_range=None,
            hours=None,
            phone=doc.get("phone") or None,
            raw_payload=doc,
        )
