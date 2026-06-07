# coding: utf-8
import logging
from typing import Any

from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient
from .utils import extract_ext, is_http_url

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15
QUALITY_PRIORITY = list(range(11))

SEARCH_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "origin": "https://y.qq.com",
    "referer": "https://y.qq.com/",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}


class QQProvider(MusicProvider):
    name = "qq"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            data = self._http.get_json(
                "https://api.vkeys.cn/v2/music/tencent/search/song",
                headers=SEARCH_HEADERS,
                params={"word": query},
                timeout=REQUEST_TIMEOUT,
            )
        except RequestException:
            LOGGER.exception("QQ search error")
            return []

        items = data.get("data", []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []
        return [item for item in (self._map_item(raw_item) for raw_item in items) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        for quality in QUALITY_PRIORITY:
            data = self._http.get_json(
                "https://api.vkeys.cn/v2/music/tencent/geturl",
                headers=SEARCH_HEADERS,
                params={"mid": song_id, "quality": quality},
                timeout=REQUEST_TIMEOUT,
            )
            if not isinstance(data, dict) or data.get("code") != 200:
                continue
            payload = data.get("data", {})
            if not isinstance(payload, dict):
                continue
            url = payload.get("url")
            if is_http_url(url):
                return PlayInfo(
                    url=url,
                    type=extract_ext(url),
                    bitrate=payload.get("kbps") or payload.get("quality"),
                    cover=payload.get("cover") or None,
                )
        raise ValueError("Failed to get play url")

    def _map_item(self, item: Any) -> MusicItem | None:
        if not isinstance(item, dict):
            return None
        song_id = item.get("mid") or ""
        if not song_id:
            return None
        return MusicItem(
            id=str(song_id),
            title=item.get("song") or "未知歌曲",
            artist=item.get("singer") or "未知歌手",
            album=item.get("album") or None,
            cover=item.get("cover") or None,
            provider=self.name,
        )
