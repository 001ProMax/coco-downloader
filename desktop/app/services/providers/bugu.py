# coding: utf-8
import logging
import re
from typing import Any

from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient
from .utils import extract_ext, is_http_url

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 20

SEARCH_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://buguyy.top",
    "priority": "u=1, i",
    "referer": "https://buguyy.top/",
    "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
}


def _normalize_duration(value: Any) -> str | None:
    if value is None:
        return None
    parts = re.findall(r"\d+", str(value))
    if not parts:
        return None

    numbers = [int(part) for part in parts[-3:]]
    while len(numbers) < 3:
        numbers.insert(0, 0)
    hours, minutes, seconds = numbers
    if hours == 0 and minutes == 0 and seconds == 0:
        return None
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class BuguProvider(MusicProvider):
    name = "bugu"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            data = self._http.get_json(
                "https://a.buguyy.top/newapi/search.php",
                headers=SEARCH_HEADERS,
                params={"keyword": query},
                timeout=REQUEST_TIMEOUT,
                verify=False,
            )
        except RequestException:
            LOGGER.exception("Bugu search error")
            return []

        payload = data.get("data", {}) if isinstance(data, dict) else {}
        items = payload.get("list", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return []
        return [item for item in (self._map_item(raw_item) for raw_item in items) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        data = self._http.get_json(
            "https://a.buguyy.top/newapi/geturl2.php",
            headers=SEARCH_HEADERS,
            params={"id": song_id},
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        url = payload.get("url") if isinstance(payload, dict) else None
        if not is_http_url(url):
            raise ValueError("Failed to get play url")
        cover = extra.get("cover") if extra and isinstance(extra.get("cover"), str) else None
        return PlayInfo(url=url, type=extract_ext(url), cover=cover)

    def _map_item(self, item: Any) -> MusicItem | None:
        if not isinstance(item, dict):
            return None
        song_id = str(item.get("id") or "")
        if not song_id:
            return None
        cover = item.get("picurl") if isinstance(item.get("picurl"), str) else None
        return MusicItem(
            id=song_id,
            title=item.get("title") or "未知歌曲",
            artist=item.get("singer") or "未知歌手",
            album=item.get("album") or None,
            cover=cover,
            duration=_normalize_duration(item.get("duration")),
            provider=self.name,
            extra={"cover": cover},
        )
