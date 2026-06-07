# coding: utf-8
import logging
from typing import Any

from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient

LOGGER = logging.getLogger(__name__)

HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "origin": "https://www.qqmp3.vip",
    "priority": "u=1, i",
    "referer": "https://www.qqmp3.vip/",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}


class QQMp3Provider(MusicProvider):
    def __init__(self, name: str = "qqmp3") -> None:
        self.name = name
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            data = self._http.get_json(
                "https://api.qqmp3.vip/api/songs.php",
                headers=HEADERS,
                params={"type": "search", "keyword": query},
            )
        except RequestException:
            LOGGER.exception("QQMp3 search error")
            return []

        items = data.get("data", []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []
        return [item for item in (self._map_item(raw_item) for raw_item in items) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        data = self._http.get_json(
            "https://api.qqmp3.vip/api/kw.php",
            headers=HEADERS,
            params={"rid": song_id, "type": "json", "level": "exhigh", "lrc": "true"},
        )
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        url = payload.get("url") if isinstance(payload, dict) else None
        if data.get("code") != 200 or not isinstance(url, str) or not url:
            raise ValueError("Failed to get play info")
        cover = payload.get("pic") if isinstance(payload.get("pic"), str) else None
        return PlayInfo(url=url, type="mp3", cover=cover)

    def _map_item(self, item: Any) -> MusicItem | None:
        if not isinstance(item, dict) or not item.get("rid"):
            return None
        return MusicItem(
            id=str(item.get("rid")),
            title=item.get("name") or "未知歌曲",
            artist=item.get("artist") or "未知歌手",
            cover=item.get("pic") or None,
            provider=self.name,
            extra={"lrc": None},
        )
