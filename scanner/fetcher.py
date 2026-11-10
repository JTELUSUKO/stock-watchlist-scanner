from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

from scanner.metrics import ET

# 5-minute bars with extended hours: Yahoo serves up to 60 days of these.
INTRADAY_INTERVAL = "5m"
INTRADAY_PERIOD = "1mo"
DAILY_PERIOD = "3mo"

# A symbol without data is reported in the scan itself; yfinance would also log it per call.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


@dataclass
class MarketData:
    """Raw bars per watchlist symbol. A symbol missing from a dict has no data."""

    daily: dict[str, pd.DataFrame] = field(default_factory=dict)
    intraday: dict[str, pd.DataFrame] = field(default_factory=dict)


def yahoo_symbol(symbol: str) -> str:
    """Yahoo writes share classes with a dash: BRK.B is BRK-B."""
    return symbol.replace(".", "-")


def _split(frame: pd.DataFrame | None, symbols: list[str]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    if frame is None or frame.empty or not isinstance(frame.columns, pd.MultiIndex):
        return out
    available = set(frame.columns.get_level_values(0))
    for symbol in symbols:
        key = yahoo_symbol(symbol)
        if key not in available:
            continue
        bars = frame[key].dropna(subset=["Close"])
        if not bars.empty:
            out[symbol] = bars
    return out


def _download(symbols: list[str], **kwargs) -> dict[str, pd.DataFrame]:
    try:
        frame = yf.download(
            [yahoo_symbol(s) for s in symbols],
            auto_adjust=False,  # alerts compare against the close that actually printed
            group_by="ticker",
            progress=False,
            threads=True,
            **kwargs,
        )
    except Exception:
        return {}
    return _split(frame, symbols)


def _download_with_retry(symbols: list[str], **kwargs) -> dict[str, pd.DataFrame]:
    result = _download(symbols, **kwargs)
    missing = [s for s in symbols if s not in result]
    if missing:
        time.sleep(2)
        result.update(_download(missing, **kwargs))
    return result


def fetch_market_data(symbols: list[str]) -> MarketData:
    """Fetch daily and extended-hours intraday bars for every symbol in two batched calls."""
    daily = _download_with_retry(symbols, period=DAILY_PERIOD, interval="1d")
    intraday = _download_with_retry(
        symbols, period=INTRADAY_PERIOD, interval=INTRADAY_INTERVAL, prepost=True
    )
    for symbol, bars in intraday.items():
        intraday[symbol] = bars.tz_convert(ET)
    return MarketData(daily=daily, intraday=intraday)
