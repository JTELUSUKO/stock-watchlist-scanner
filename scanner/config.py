from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml


class ConfigError(ValueError):
    """The config or watchlist file can't be used as written."""


@dataclass(frozen=True)
class Config:
    price_change_pct: float = 2.0
    volume_spike_ratio: float = 1.5
    lookback_days: int = 20
    news_enabled: bool = True
    news_max_headlines: int = 1
    output_format: str = "table"
    show_all: bool = True


def _positive(section: dict, key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{key} must be a positive number, got {value!r}")
    return value


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping of settings")

    alerts = data.get("alerts") or {}
    scan = data.get("scan") or {}
    news = data.get("news") or {}
    output = data.get("output") or {}
    defaults = Config()

    output_format = output.get("format", defaults.output_format)
    if output_format not in ("table", "json"):
        raise ConfigError(f"output.format must be 'table' or 'json', got {output_format!r}")

    return Config(
        price_change_pct=float(_positive(alerts, "price_change_pct", defaults.price_change_pct)),
        volume_spike_ratio=float(_positive(alerts, "volume_spike_ratio", defaults.volume_spike_ratio)),
        lookback_days=int(_positive(scan, "lookback_days", defaults.lookback_days)),
        news_enabled=bool(news.get("enabled", defaults.news_enabled)),
        news_max_headlines=int(_positive(news, "max_headlines", defaults.news_max_headlines)),
        output_format=output_format,
        show_all=bool(output.get("show_all", defaults.show_all)),
    )


def load_watchlist(path: Path) -> list[tuple[str, str]]:
    """Return (symbol, name) pairs in file order, without duplicates."""
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ConfigError(f"Watchlist not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc

    entries = data.get("stocks") if isinstance(data, dict) else data
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path} needs a non-empty \"stocks\" list")

    stocks: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            entry = {"symbol": entry}
        symbol = str(entry.get("symbol", "")).strip().upper() if isinstance(entry, dict) else ""
        if not symbol:
            raise ConfigError(f"Watchlist entry has no symbol: {entry!r}")
        if symbol in seen:
            continue
        seen.add(symbol)
        stocks.append((symbol, str(entry.get("name") or symbol)))
    return stocks
