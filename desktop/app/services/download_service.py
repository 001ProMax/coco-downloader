# coding: utf-8
import re
from pathlib import Path
from typing import Any

import requests
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from app.common.config import DownloadFilenameRule, cfg
from app.common.signal_bus import signalBus
from app.models.music import MusicItem, PlayInfo
from app.services.providers import get_provider

DOWNLOAD_TIMEOUT = 30
DOWNLOAD_CHUNK_SIZE = 1024 * 256
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _safe_filename(value: str) -> str:
    filename = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return filename or "music"


class DownloadThread(QThread):
    """Resolve and download a music file without blocking the UI."""

    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        item: MusicItem,
        extra_overrides: dict[str, Any] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.extra_overrides = extra_overrides or {}

    def run(self) -> None:
        try:
            provider = get_provider(self.item.provider)
            extra = dict(self.item.extra)
            extra.update(self.extra_overrides)
            if self.item.cover:
                extra["cover"] = self.item.cover

            play_info = provider.get_play_info(self.item.id, extra)
            file_path = self._download(play_info)
            self.finished.emit(str(file_path))
        except Exception as error:
            self.failed.emit(str(error) or "下载失败")

    def _download(self, play_info: PlayInfo) -> Path:
        download_dir = Path(cfg.get(cfg.downloadFolder))
        download_dir.mkdir(parents=True, exist_ok=True)

        with requests.get(
            play_info.url,
            headers={**REQUEST_HEADERS, **play_info.headers},
            timeout=DOWNLOAD_TIMEOUT,
            stream=True,
        ) as response:
            response.raise_for_status()
            chunks = response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE)
            first_chunk = next(chunks, b"")
            suffix = self._suffix(play_info, first_chunk)
            file_path = self._unique_file_path(download_dir, suffix)
            with file_path.open("wb") as file:
                if first_chunk:
                    file.write(first_chunk)
                for chunk in chunks:
                    if chunk:
                        file.write(chunk)

        return file_path

    def _unique_file_path(self, download_dir: Path, suffix: str) -> Path:
        base_name = _safe_filename(self._filename_stem())
        file_path = download_dir / f"{base_name}.{suffix}"
        if not file_path.exists():
            return file_path

        for index in range(1, 1000):
            candidate = download_dir / f"{base_name} ({index}).{suffix}"
            if not candidate.exists():
                return candidate
        return download_dir / f"{base_name}.{suffix}"

    def _filename_stem(self) -> str:
        rule = cfg.get(cfg.downloadFilenameRule)
        if rule == DownloadFilenameRule.TITLE:
            return self.item.title
        if rule == DownloadFilenameRule.TITLE_ID:
            return f"{self.item.title} - {self.item.id}"
        if rule == DownloadFilenameRule.ARTIST_TITLE:
            return f"{self.item.artist} - {self.item.title}"
        return f"{self.item.title} - {self.item.artist}"

    def _suffix(self, play_info: PlayInfo, first_chunk: bytes) -> str:
        detected_suffix = self._suffix_from_header(first_chunk)
        if detected_suffix:
            return detected_suffix

        suffix = str(play_info.type or "").strip().lower().lstrip(".")
        if suffix:
            return suffix
        clean_url = play_info.url.split("?", 1)[0]
        if "." in clean_url:
            return clean_url.rsplit(".", 1)[-1].lower()
        return "mp3"

    def _suffix_from_header(self, first_chunk: bytes) -> str:
        if len(first_chunk) < 4:
            return ""
        if first_chunk.startswith(b"ID3") or first_chunk[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
            return "mp3"
        if first_chunk[:2] in {b"\xff\xf1", b"\xff\xf9"}:
            return "aac"
        if first_chunk[4:8] == b"ftyp":
            return "m4a"
        return ""


class DownloadService(QObject):
    """Global download coordinator."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.threads: set[DownloadThread] = set()
        signalBus.downloadRequested.connect(self.start_download)

    def start_download(self, item: MusicItem, extra_overrides: object = None) -> None:
        overrides = extra_overrides if isinstance(extra_overrides, dict) else {}
        thread = DownloadThread(item, overrides, self)
        self.threads.add(thread)
        signalBus.downloadStarted.emit(f"{item.title} - {item.artist}")
        thread.finished.connect(self._on_finished)
        thread.failed.connect(self._on_failed)
        thread.finished.connect(lambda *_: self._remove_thread(thread))
        thread.failed.connect(lambda *_: self._remove_thread(thread))
        thread.finished.connect(thread.deleteLater)
        thread.failed.connect(thread.deleteLater)
        thread.start()

    def _on_finished(self, file_path: str) -> None:
        signalBus.downloadFinished.emit(file_path)

    def _on_failed(self, message: str) -> None:
        signalBus.downloadFailed.emit(message)

    def _remove_thread(self, thread: DownloadThread) -> None:
        self.threads.discard(thread)
