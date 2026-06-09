# coding: utf-8
from .aiting import AitingProvider
from .base import MusicProvider
from .bodian import BodianProvider
from .bugu import BuguProvider
from .gequbao import GequbaoProvider
from .gequhai import GequhaiProvider
from .jianbin import JianbinProvider
from .joox import JooxProvider
from .kugou import KugouProvider
from .livepoo import LivepooProvider
from .migu import MiguProvider
from .netease_official import NeteaseOfficialProvider
from .qq import QQProvider
from .qq_official import QQOfficialProvider
from .qqmp3 import QQMp3Provider

PROVIDERS: dict[str, MusicProvider] = {
    "netease-official": NeteaseOfficialProvider(),
    "qq-official": QQOfficialProvider(),
    "kugou": KugouProvider(),
    "gequbao": GequbaoProvider(),
    "gequhai": GequhaiProvider(),
    "bugu": BuguProvider(),
    "bodian": BodianProvider(),
    "qq": QQProvider(),
    "qqmp3": QQMp3Provider(),
    "mitu": QQMp3Provider("mitu"),
    "joox": JooxProvider(),
    "migu": MiguProvider(),
    "livepoo": LivepooProvider(),
    "aiting": AitingProvider(),
    "jianbin-netease": JianbinProvider("jianbin-netease", "netease"),
    "jianbin-qq": JianbinProvider("jianbin-qq", "qq"),
    "jianbin-kugou": JianbinProvider("jianbin-kugou", "kugou"),
    "jianbin-kuwo": JianbinProvider("jianbin-kuwo", "kuwo"),
}

PROVIDER_DISPLAY_NAMES = {
    "网易云音乐": "netease-official",
    "QQ音乐": "qq-official",
    "酷狗音乐": "kugou",
    "歌曲宝": "gequbao",
    "歌曲海": "gequhai",
    "布谷": "bugu",
    "波点": "bodian",
    "QQ音乐(MP3)": "qqmp3",
    "米兔": "mitu",
    "JOOX": "joox",
    "咪咕": "migu",
    "力音": "livepoo",
    "爱听": "aiting",
    "煎饼-网易云": "jianbin-netease",
    "煎饼-QQ": "jianbin-qq",
    "煎饼-酷狗": "jianbin-kugou",
    "煎饼-酷我": "jianbin-kuwo",
}


def get_provider(name: str = "netease-official") -> MusicProvider:
    provider_key = PROVIDER_DISPLAY_NAMES.get(name, name)
    return PROVIDERS.get(provider_key) or PROVIDERS["netease-official"]


def get_all_providers() -> list[MusicProvider]:
    return list(PROVIDERS.values())


__all__ = [
    "MusicProvider",
    "PROVIDER_DISPLAY_NAMES",
    "get_all_providers",
    "get_provider",
]
