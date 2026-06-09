# coding: utf-8
import base64
import logging
from typing import Any

from app.models.music import LyricData, MusicItem, PlayInfo
from app.services.errors import ProviderNetworkError

from .base import MusicProvider
from .http_client import ProviderHttpClient
from .utils import clean_lyric, extract_ext, is_http_url, parse_lrc_lines

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15
SEARCH_API_URL = "https://songsearch.kugou.com/song_search_v2"
CGG_API_URL = "https://music-api2.cenguigui.cn/"
LYRIC_SEARCH_URL = "http://lyrics.kugou.com/search"
LYRIC_DOWNLOAD_URL = "http://lyrics.kugou.com/download"
HAITANG_API_URLS = [
    "https://musicapi.haitangw.net/kgqq/kg.php",
    "https://music.haitangw.cc/kgqq/kg.php",
]
SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    )
}
KUGOU_DOWNLOAD_OPTIONS = [
    # {"value": "cenguigui-lossless", "parser": "cenguigui", "level": "lossless", "label": "无损音质", "quality": "lossless", "format": "flac/mp3"},
    # {"value": "cenguigui-exhigh", "parser": "cenguigui", "level": "exhigh", "label": "高品质", "quality": "exhigh", "format": "mp3/flac"},
    # {"value": "cenguigui-standard", "parser": "cenguigui", "level": "standard", "label": "标准音质", "quality": "standard", "format": "mp3"},
    {"value": "haitang-hires", "parser": "haitang", "level": "hires", "label": "Hi-Res 音质", "quality": "hires", "format": "flac"},
    {"value": "haitang-lossless", "parser": "haitang", "level": "lossless", "label": "无损音质", "quality": "lossless", "format": "flac/mp3"},
    {"value": "haitang-exhigh", "parser": "haitang", "level": "exhigh", "label": "高品质", "quality": "exhigh", "format": "mp3/flac"},
]


def _normalize_limit(limit: int) -> int:
    return min(max(int(limit), 1), 30)


def _normalize_offset(offset: int) -> int:
    return max(int(offset), 0)


def _format_duration(seconds: Any) -> str | None:
    if not isinstance(seconds, int | float):
        return None
    normalized = int(seconds / 1000) if seconds > 10000 else int(seconds)
    return f"{normalized // 60:02d}:{normalized % 60:02d}"


def _normalize_cover(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.replace("{size}", "400")


def _string_value(value: Any) -> str:
    return str(value).strip() if isinstance(value, str | int | float) else ""


class KugouProvider(MusicProvider):
    name = "kugou"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        page_size = _normalize_limit(limit)
        page = (_normalize_offset(offset) // page_size) + 1
        try:
            data = self._http.get_json(
                SEARCH_API_URL,
                headers=SEARCH_HEADERS,
                params={
                    "format": "json",
                    "keyword": query.strip(),
                    "platform": "WebFilter",
                    "page": page,
                    "pagesize": page_size,
                },
                timeout=REQUEST_TIMEOUT,
            )
        except ProviderNetworkError:
            LOGGER.exception("Kugou search error")
            return []

        payload = data.get("data", {}) if isinstance(data, dict) else {}
        items = payload.get("lists", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return []
        return [item for item in (self._map_item(raw_item) for raw_item in items) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        context = extra or {}
        fallback_cover = _string_value(context.get("cover")) or None
        if context.get("usage") == "playback":
            return self._to_play_info(self._get_playback_url(song_id), fallback_cover)

        selected_parser = str(context.get("selectedParser") or "").strip()
        selected_level = str(context.get("selectedLevel") or "").strip()

        if selected_parser == "cenguigui":
            return self._to_play_info(self._get_by_cenguigui(song_id, self._selected_levels(selected_level)), fallback_cover)
        if selected_parser == "haitang":
            return self._to_play_info(self._get_by_haitang(song_id, self._selected_levels(selected_level)), fallback_cover)

        try:
            return self._to_play_info(self._get_by_cenguigui(song_id), fallback_cover)
        except (ProviderNetworkError, ValueError):
            LOGGER.warning("Kugou cenguigui fallback failed", exc_info=True)
        return self._to_play_info(self._get_by_haitang(song_id), fallback_cover)

    def get_lyric(self, song_id: str, extra: dict[str, Any] | None = None) -> LyricData:
        context = extra or {}
        keyword = _string_value(context.get("filename"))
        duration = _string_value(context.get("duration")) or "-1"
        search_data = self._http.get_json(
            LYRIC_SEARCH_URL,
            params={"keyword": keyword, "duration": duration, "hash": song_id},
            timeout=REQUEST_TIMEOUT,
        )
        candidate = self._first_lyric_candidate(search_data)
        if not candidate:
            return LyricData(songid=song_id, provider=self.name, lines=[], lrc="")

        lyric_data = self._http.get_json(
            LYRIC_DOWNLOAD_URL,
            params={
                "ver": 1,
                "client": "pc",
                "id": candidate["id"],
                "accesskey": candidate["accesskey"],
                "fmt": "lrc",
                "charset": "utf8",
            },
            timeout=REQUEST_TIMEOUT,
        )
        encoded = lyric_data.get("content", "") if isinstance(lyric_data, dict) else ""
        lyric = self._decode_lyric(encoded)
        return LyricData(songid=song_id, provider=self.name, lines=parse_lrc_lines(lyric), lrc=lyric)

    def _map_item(self, item: Any) -> MusicItem | None:
        if not isinstance(item, dict):
            return None

        song_id = _string_value(item.get("FileHash") or item.get("hash"))
        if not song_id:
            return None

        title = _string_value(item.get("SongName") or item.get("songname"))
        filename = _string_value(item.get("FileName") or item.get("filename"))
        artist = _string_value(item.get("SingerName") or item.get("singername"))
        duration = item.get("Duration") or item.get("duration") or item.get("timelen")
        cover = self._extract_cover(item)
        return MusicItem(
            id=song_id,
            title=title or filename or "未知歌曲",
            artist=artist or "未知歌手",
            album=_string_value(item.get("AlbumName") or item.get("album_name")) or None,
            cover=cover,
            duration=_format_duration(duration),
            provider=self.name,
            extra={
                "cover": cover,
                "selectedOption": "haitang-exhigh",
                "selectedParser": "haitang",
                "selectedLevel": "exhigh",
                "selectedFormat": "flac",
                "qualityOptions": KUGOU_DOWNLOAD_OPTIONS,
                "filename": filename or f"{title} - {artist}",
                "duration": duration or -1,
            },
        )

    def _extract_cover(self, item: dict[str, Any]) -> str | None:
        trans_param = item.get("trans_param")
        union_cover = trans_param.get("union_cover") if isinstance(trans_param, dict) else None
        return _normalize_cover(union_cover or item.get("cover_url") or item.get("Image"))

    def _get_playback_url(self, song_id: str) -> dict[str, str | None]:
        try:
            return self._get_by_haitang(song_id, ("exhigh", "lossless", "hires"))
        except ValueError as error:
            LOGGER.warning("Kugou haitang playback parser failed: %s", error)

        try:
            return self._get_by_cenguigui(song_id)
        except (ProviderNetworkError, ValueError) as error:
            LOGGER.warning("Kugou cenguigui playback parser failed: %s", error)
            raise

    def _get_by_cenguigui(
        self,
        song_id: str,
        levels: tuple[str, ...] | None = None,
    ) -> dict[str, str | None]:
        for level in levels or ("lossless", "exhigh", "standard"):
            data = self._http.get_json(
                CGG_API_URL,
                params={"kg": "", "id": song_id, "type": "song", "format": "json", "level": level},
                timeout=REQUEST_TIMEOUT,
            )
            payload = data.get("data", {}) if isinstance(data, dict) else {}
            url = str(payload.get("url") or "").strip() if isinstance(payload, dict) else ""
            if not is_http_url(url):
                continue
            cover = payload.get("pic") if isinstance(payload.get("pic"), str) else None
            return {"url": url, "bitrate": level, "cover": cover}
        raise ValueError("Failed to get cenguigui url")

    def _get_by_haitang(
        self,
        song_id: str,
        levels: tuple[str, ...] | None = None,
    ) -> dict[str, str | None]:
        for api_url in HAITANG_API_URLS:
            for level in levels or ("hires", "lossless", "exhigh"):
                info = self._try_haitang(api_url, song_id, level)
                if info:
                    return info
        raise ValueError("Failed to get haitang url")

    def _try_haitang(
        self,
        api_url: str,
        song_id: str,
        level: str,
    ) -> dict[str, str | None] | None:
        try:
            data = self._http.get_json(
                api_url,
                params={"type": "json", "id": song_id, "level": level},
                timeout=REQUEST_TIMEOUT,
            )
        except ProviderNetworkError:
            return None

        payload = data.get("data", {}) if isinstance(data, dict) else {}
        url = str(payload.get("url") or "").strip() if isinstance(payload, dict) else ""
        if not is_http_url(url):
            return None
        return {"url": url, "bitrate": level, "cover": None}

    def _selected_levels(self, selected_level: str) -> tuple[str, ...] | None:
        return (selected_level,) if selected_level else None

    def _to_play_info(self, info: dict[str, str | None], fallback_cover: str | None) -> PlayInfo:
        url = str(info["url"])
        file_type = extract_ext(url)
        LOGGER.info("Kugou resolved play url: bitrate=%s, type=%s", info.get("bitrate"), file_type)
        return PlayInfo(
            url=url,
            type=file_type,
            bitrate=info.get("bitrate"),
            cover=info.get("cover") or fallback_cover,
            headers=SEARCH_HEADERS,
        )

    def _first_lyric_candidate(self, data: Any) -> dict[str, Any] | None:
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
        if not isinstance(candidates, list) or not candidates:
            return None
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            return None
        if not candidate.get("id") or not candidate.get("accesskey"):
            return None
        return candidate

    def _decode_lyric(self, encoded: Any) -> str:
        if not isinstance(encoded, str) or not encoded:
            return ""
        try:
            return clean_lyric(base64.b64decode(encoded).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return ""
