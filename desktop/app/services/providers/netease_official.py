# coding: utf-8
import hashlib
import json
import logging
import random
import string
from typing import Any
from urllib.parse import urlencode

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15
API_DOMAIN = "https://interface.music.163.com"
EAPI_KEY = b"e82ckenh8dichen8"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 "
    "NeteasyMusicDesktop/3.1.19.204510"
)
DEFAULT_HEADER = {
    "os": "pc",
    "appver": "3.1.19.204510",
    "requestId": "0",
    "osver": "Microsoft-Windows-11-Home-China-build-22631-64bit",
}


def _normalize_limit(limit: int) -> int:
    return min(max(int(limit), 1), 50)


def _normalize_offset(offset: int) -> int:
    return max(int(offset), 0)


def _format_duration(milliseconds: Any) -> str | None:
    if not isinstance(milliseconds, int | float):
        return None
    seconds = int(milliseconds / 1000)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _join_artists(items: Any) -> str:
    if not isinstance(items, list):
        return ""

    names = []
    for item in items:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return ", ".join(names)


def _eapi_encrypt(uri: str, payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    digest_text = f"nobody{uri}use{text}md5forencrypt"
    digest = hashlib.md5(digest_text.encode("utf-8")).hexdigest()
    message = f"{uri}-36cd479b6b5-{text}-36cd479b6b5-{digest}"
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(message.encode("utf-8"), AES.block_size))
    return encrypted.hex().upper()


def _eapi_decrypt(content: bytes) -> Any:
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(content), AES.block_size)
    return json.loads(decrypted.decode("utf-8"))


class NeteaseOfficialProvider(MusicProvider):
    name = "netease-official"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()
        self._device_id = self._generate_device_id()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            payload = self._make_request(
                "/api/cloudsearch/pc",
                {
                    "s": query,
                    "type": 1,
                    "limit": _normalize_limit(limit),
                    "offset": _normalize_offset(offset),
                    "total": True,
                },
            )
        except (RequestException, ValueError, json.JSONDecodeError):
            LOGGER.exception("Netease official search error")
            return []

        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        songs = result.get("songs", []) if isinstance(result, dict) else []
        if not isinstance(songs, list):
            return []
        return [item for item in (self._map_item(song) for song in songs) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        raise NotImplementedError("Netease official provider only supports search now")

    def _make_request(self, uri: str, data: dict[str, Any]) -> Any:
        url = f"{API_DOMAIN}/eapi{uri[4:]}"
        encrypted = _eapi_encrypt(uri, {"header": self._build_request_header(), "e_r": True, **data})
        response = self._http.post_response(
            url,
            headers={
                "User-Agent": DEFAULT_UA,
                "Cookie": self._build_cookie_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"params": encrypted},
            timeout=REQUEST_TIMEOUT,
        )
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return _eapi_decrypt(response.content)

    def _build_request_header(self) -> dict[str, str]:
        return {**DEFAULT_HEADER, "deviceId": self._device_id, "MUSIC_U": ""}

    def _build_cookie_header(self) -> str:
        cookies = self._build_request_header()
        return urlencode(cookies).replace("&", "; ")

    def _generate_device_id(self) -> str:
        alphabet = string.ascii_lowercase + string.digits
        return "".join(random.choice(alphabet) for _ in range(32))

    def _map_item(self, song: Any) -> MusicItem | None:
        if not isinstance(song, dict):
            return None
        song_id = song.get("id")
        if not isinstance(song_id, int | str):
            return None

        artists = song.get("ar") if isinstance(song.get("ar"), list) else song.get("artists")
        album = song.get("al") if isinstance(song.get("al"), dict) else song.get("album")
        album_name = album.get("name") if isinstance(album, dict) else None
        cover = album.get("picUrl") if isinstance(album, dict) else None
        duration = song.get("dt") if isinstance(song.get("dt"), int | float) else song.get("duration")

        return MusicItem(
            id=str(song_id),
            title=song.get("name") or "未知歌曲",
            artist=_join_artists(artists) or "未知歌手",
            album=str(album_name) if album_name else None,
            cover=str(cover) if cover else None,
            duration=_format_duration(duration),
            provider=self.name,
        )
