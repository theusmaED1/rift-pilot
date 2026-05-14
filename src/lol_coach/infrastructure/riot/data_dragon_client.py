"""Cliente do Data Dragon com cache em disco para nomes/preços pt-BR."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from lol_coach.settings.constants import Network, Timing

_CACHE_DIR = Path.home() / ".lol_coach"
_CHAMPION_MAP_FILE = _CACHE_DIR / "champion_map.json"
_ITEM_DATA_FILE = _CACHE_DIR / "item_data_pt.json"
_RUNE_NAMES_FILE = _CACHE_DIR / "rune_names_pt.json"
_DEEPLOL_VERSION_FILE = _CACHE_DIR / "deeplol_version.json"


class DataDragonClient:
    """Resolve IDs e nomes localizados de campeões, itens e runas.

    Cacheia tudo em `~/.lol_coach/` invalidando por versão do patch.
    """

    def __init__(self) -> None:
        self._champion_map_cache: dict[str, Any] | None = None
        self._item_data_cache: dict[int, dict[str, Any]] | None = None
        self._rune_names_cache: dict[int, str] | None = None
        self._deeplol_version_cache: str = ""
        self._deeplol_version_fetched_at_seconds: float = 0.0

    # ── Campeões ─────────────────────────────────────────────────────────────

    def get_champion_id(self, champion_name: str) -> int | None:
        data = self._load_champion_map()
        info = data["champions"].get(champion_name)
        return info["key"] if info else None

    def get_data_dragon_version(self) -> str:
        return self._load_champion_map()["version"]

    # ── Itens ────────────────────────────────────────────────────────────────

    def get_item_names(self) -> dict[int, str]:
        return {iid: data["name"] for iid, data in self._load_item_data().items()}

    def get_item_prices(self) -> dict[int, int]:
        return {iid: data["price"] for iid, data in self._load_item_data().items()}

    # ── Runas ────────────────────────────────────────────────────────────────

    def get_rune_names(self) -> dict[int, str]:
        if self._rune_names_cache is not None:
            return self._rune_names_cache

        version = self.get_data_dragon_version()
        cached = _read_versioned_cache(_RUNE_NAMES_FILE, version)
        if cached is not None:
            self._rune_names_cache = {int(k): v for k, v in cached.items()}
            return self._rune_names_cache

        url = Network.DATA_DRAGON_RUNES_URL_TEMPLATE.format(version=version)
        response = httpx.get(url, timeout=Timing.DATA_DRAGON_HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        trees = response.json()

        names: dict[int, str] = {}
        for tree in trees:
            names[tree["id"]] = tree["name"]
            for slot in tree.get("slots", []):
                for rune in slot.get("runes", []):
                    names[rune["id"]] = rune["name"]

        _write_versioned_cache(_RUNE_NAMES_FILE, version, names)
        self._rune_names_cache = names
        return names

    # ── Deeplol version ──────────────────────────────────────────────────────

    def get_deeplol_recent_version(self) -> str:
        """Versão mais recente do patch segundo o deeplol (cache de 1h)."""
        now = time.monotonic()
        if (
            self._deeplol_version_cache
            and (now - self._deeplol_version_fetched_at_seconds)
            < Timing.DATA_DRAGON_VERSION_CACHE_TTL_SECONDS
        ):
            return self._deeplol_version_cache

        if _DEEPLOL_VERSION_FILE.exists():
            try:
                with _DEEPLOL_VERSION_FILE.open(encoding="utf-8") as f:
                    cached = json.load(f)
                if (
                    now - cached.get("fetched_at", 0)
                    < Timing.DATA_DRAGON_VERSION_CACHE_TTL_SECONDS
                ):
                    self._deeplol_version_cache = cached["version"]
                    self._deeplol_version_fetched_at_seconds = cached["fetched_at"]
                    return self._deeplol_version_cache
            except Exception:
                pass

        response = httpx.get(
            "https://b2c-api-cdn.deeplol.gg/champion/version?cnt=1",
            timeout=Timing.DEEPLOL_HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        version = response.json()["recent_version"]

        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with _DEEPLOL_VERSION_FILE.open("w", encoding="utf-8") as f:
            json.dump({"version": version, "fetched_at": now}, f)

        self._deeplol_version_cache = version
        self._deeplol_version_fetched_at_seconds = now
        return version

    # ── Helpers privados ─────────────────────────────────────────────────────

    def _load_champion_map(self) -> dict[str, Any]:
        if self._champion_map_cache is not None:
            return self._champion_map_cache

        cached = _read_json(_CHAMPION_MAP_FILE)
        if cached is not None:
            self._champion_map_cache = cached
            return cached

        version = self._fetch_latest_data_dragon_version()
        url = Network.DATA_DRAGON_CHAMPION_URL_TEMPLATE.format(version=version)
        response = httpx.get(url, timeout=Timing.DATA_DRAGON_HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        raw_champions = response.json()["data"]

        champions = {
            champion_id: {"key": int(payload["key"]), "slug": champion_id.lower()}
            for champion_id, payload in raw_champions.items()
        }
        data = {"version": version, "champions": champions}
        _write_json(_CHAMPION_MAP_FILE, data)
        self._champion_map_cache = data
        return data

    def _load_item_data(self) -> dict[int, dict[str, Any]]:
        if self._item_data_cache is not None:
            return self._item_data_cache

        version = self.get_data_dragon_version()
        cached = _read_versioned_cache(_ITEM_DATA_FILE, version)
        if cached is not None:
            self._item_data_cache = {int(k): v for k, v in cached.items()}
            return self._item_data_cache

        url = Network.DATA_DRAGON_ITEM_URL_TEMPLATE.format(version=version)
        response = httpx.get(url, timeout=Timing.DATA_DRAGON_HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        raw_items = response.json()["data"]

        items = {
            int(item_id): {"name": payload["name"], "price": payload["gold"]["total"]}
            for item_id, payload in raw_items.items()
        }
        _write_versioned_cache(_ITEM_DATA_FILE, version, items)
        self._item_data_cache = items
        return items

    @staticmethod
    def _fetch_latest_data_dragon_version() -> str:
        response = httpx.get(
            Network.DATA_DRAGON_VERSIONS_URL,
            timeout=Timing.DATA_DRAGON_HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()[0]


# ── Cache helpers ────────────────────────────────────────────────────────────


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _read_versioned_cache(path: Path, version: str) -> dict[str, Any] | None:
    raw = _read_json(path)
    if raw is None or raw.get("version") != version:
        return None
    return raw.get("data") or {}


def _write_versioned_cache(path: Path, version: str, data: dict[int, Any]) -> None:
    _write_json(path, {"version": version, "data": {str(k): v for k, v in data.items()}})
