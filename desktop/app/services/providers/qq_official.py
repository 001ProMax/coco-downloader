# coding: utf-8
import logging
from typing import Any

from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15
SEARCH_URL = "http://u6.y.qq.com/cgi-bin/musicu.fcg"
SEARCH_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
        "Mobile/15E148 Safari/604.1 Edg/131.0.0.0"
    ),
}


def _normalize_limit(limit: int) -> int:
    return min(max(int(limit), 1), 30)


def _normalize_offset(offset: int) -> int:
    return max(int(offset), 0)


def _format_duration(seconds: Any) -> str | None:
    if not isinstance(seconds, int | float):
        return None
    value = int(seconds)
    return f"{value // 60:02d}:{value % 60:02d}"


def _join_singers(items: Any) -> str:
    if not isinstance(items, list):
        return ""

    names = []
    for item in items:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return ", ".join(names)


class QQOfficialProvider(MusicProvider):
    name = "qq-official"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        page_size = _normalize_limit(limit)
        page_num = (_normalize_offset(offset) // page_size) + 1
        payload = self._build_payload(query, page_size, page_num)

        try:
            data = self._http.post_json(
                SEARCH_URL,
                headers=SEARCH_HEADERS,
                json_data=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except RequestException:
            LOGGER.exception("QQ official search error")
            return []

        if not isinstance(data, dict) or data.get("code") != 0:
            LOGGER.warning("QQ official search failed: %s", data)
            return []

        song_node = self._extract_song_node(data)
        songs = song_node.get("list", []) if isinstance(song_node, dict) else []
        if not isinstance(songs, list):
            return []
        return [item for item in (self._map_item(song) for song in songs) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        raise NotImplementedError("QQ official provider only supports search now")

    def _build_payload(self, query: str, limit: int, page_num: int) -> dict[str, Any]:
        return {
            "comm": {
                "ct": "19",
                "cv": "1859",
                "uin": "0",
            },
            "req_1": {
                "method": "DoSearchForQQMusicDesktop",
                "module": "music.search.SearchCgiService",
                "param": {
                    "grp": 1,
                    "num_per_page": limit,
                    "page_num": page_num,
                    "query": query,
                    "search_type": 0,
                },
            },
        }

    def _extract_song_node(self, data: dict[str, Any]) -> dict[str, Any] | None:
        request_data = data.get("req_1", {})
        if not isinstance(request_data, dict):
            return None
        body_data = request_data.get("data", {})
        if not isinstance(body_data, dict):
            return None
        body = body_data.get("body", {})
        if not isinstance(body, dict):
            return None
        song_node = body.get("song", {})
        return song_node if isinstance(song_node, dict) else None

    def _map_item(self, song: Any) -> MusicItem | None:
        if not isinstance(song, dict):
            return None

        song_id = song.get("id")
        song_mid = song.get("mid")
        item_id = song_mid if isinstance(song_mid, str) and song_mid else song_id
        if not isinstance(item_id, int | str):
            return None

        album = song.get("album", {})
        album_name = album.get("name") if isinstance(album, dict) else None
        album_mid = album.get("mid") if isinstance(album, dict) else None
        cover = None
        if isinstance(album_mid, str) and album_mid:
            cover = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg"

        return MusicItem(
            id=str(item_id),
            title=song.get("name") or "未知歌曲",
            artist=_join_singers(song.get("singer")) or "未知歌手",
            album=str(album_name) if album_name else None,
            cover=cover,
            duration=_format_duration(song.get("interval")),
            provider=self.name,
            extra={"mid": song_mid} if isinstance(song_mid, str) and song_mid else {},
        )
