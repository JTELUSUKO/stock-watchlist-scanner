from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf


@dataclass
class StockSnapshot:
    symbol: str
    name: str
    price: float | None
    prev_close: float | None
    change_pct: float | None
    volume: int | None
    avg_volume_20d: float | None
    volume_ratio: float | None
    error: str | None = None


def fetch_snapshot(symbol: str, name: str, period: str = "1mo") -> StockSnapshot:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        history = ticker.history(period=period, interval="1d")

        price = getattr(info, "last_price", None) or getattr(info, "regular_market_price", None)
        prev_close = getattr(info, "previous_close", None)

        if price is None and not history.empty:
            price = float(history["Close"].iloc[-1])
        if prev_close is None and len(history) >= 2:
            prev_close = float(history["Close"].iloc[-2])

        change_pct = None
        if price is not None and prev_close:
            change_pct = ((price - prev_close) / prev_close) * 100

        volume = int(history["Volume"].iloc[-1]) if not history.empty else None
        avg_volume_20d = None
        volume_ratio = None
        if not history.empty and "Volume" in history:
            recent = history["Volume"].tail(20)
            avg_volume_20d = float(recent.mean())
            if volume and avg_volume_20d:
                volume_ratio = volume / avg_volume_20d

        return StockSnapshot(
            symbol=symbol,
            name=name,
            price=round(price, 2) if price is not None else None,
            prev_close=round(prev_close, 2) if prev_close is not None else None,
            change_pct=round(change_pct, 2) if change_pct is not None else None,
            volume=volume,
            avg_volume_20d=round(avg_volume_20d) if avg_volume_20d else None,
            volume_ratio=round(volume_ratio, 2) if volume_ratio else None,
        )
    except Exception as exc:
        return StockSnapshot(
            symbol=symbol,
            name=name,
            price=None,
            prev_close=None,
            change_pct=None,
            volume=None,
            avg_volume_20d=None,
            volume_ratio=None,
            error=str(exc),
        )
