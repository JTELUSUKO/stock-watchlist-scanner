"""Turn raw bars into one snapshot per stock. Pure calculation, no network."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Mapping
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
BAR = timedelta(minutes=5)
# Fewer prior days than this and an average volume isn't worth comparing against.
MIN_VOLUME_DAYS = 5

PRE = "pre-market"
REGULAR = "regular"
POST = "after-hours"
CLOSED = "closed"


@dataclass(frozen=True)
class Session:
    phase: str
    date: date  # the trading day the figures describe


@dataclass
class StockSnapshot:
    symbol: str
    name: str
    price: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    gap_pct: float | None = None
    volume: int | None = None
    avg_volume: float | None = None
    rel_volume: float | None = None
    as_of: datetime | None = None
    error: str | None = None


def detect_session(now: datetime, intraday: Mapping[str, pd.DataFrame]) -> Session:
    """Work out the trading day from the data, so holidays and weekends need no calendar."""
    now_et = now.astimezone(ET)
    last_dates = [bars.index[-1].date() for bars in intraday.values() if len(bars)]
    if not last_dates or max(last_dates) != now_et.date():
        return Session(CLOSED, max(last_dates) if last_dates else now_et.date())
    clock = now_et.time()
    if clock < MARKET_OPEN:
        return Session(PRE, now_et.date())
    if clock < MARKET_CLOSE:
        return Session(REGULAR, now_et.date())
    return Session(POST, now_et.date())


def _dates(frame: pd.DataFrame):
    return frame.index.date


def _regular_hours(bars: pd.DataFrame) -> pd.DataFrame:
    clock = bars.index.time
    return bars[(clock >= MARKET_OPEN) & (clock < MARKET_CLOSE)]


def usual_share_of_day(
    intraday: pd.DataFrame,
    daily: pd.DataFrame,
    session_date: date,
    now: datetime,
    lookback_days: int,
) -> float | None:
    """The share of a day's volume that has usually traded by this time of day.

    Each earlier day's volume so far is measured against that day's full daily volume,
    which includes the closing auction the intraday bars leave out. The median over days
    is used so one day with a bad print doesn't move it, and the bar still filling counts
    for the part of it that has elapsed.
    """
    now_et = now.astimezone(ET)
    regular = _regular_hours(intraday)
    earlier = regular[_dates(regular) < session_date]
    if earlier.empty:
        return None
    anchor = datetime.combine(session_date, time(0), tzinfo=ET)
    minutes_now = (now_et - anchor).total_seconds() / 60
    bar_starts = earlier.index.hour * 60 + earlier.index.minute
    bar_minutes = BAR.total_seconds() / 60
    elapsed = ((minutes_now - bar_starts) / bar_minutes).to_numpy().clip(0, 1)

    so_far = (earlier["Volume"] * elapsed).groupby(_dates(earlier)).sum()
    totals = pd.Series(daily["Volume"].to_numpy(), index=_dates(daily)).reindex(so_far.index)
    shares = (so_far / totals)[totals > 0].clip(upper=1).tail(lookback_days)
    if len(shares) < MIN_VOLUME_DAYS:
        return None
    share = float(shares.median())
    return share if share > 0 else None


def build_snapshot(
    symbol: str,
    name: str,
    daily: pd.DataFrame | None,
    intraday: pd.DataFrame | None,
    session: Session,
    now: datetime,
    lookback_days: int = 20,
) -> StockSnapshot:
    snap = StockSnapshot(symbol=symbol, name=name)
    if daily is None or daily.empty:
        snap.error = "No price data from Yahoo (check the symbol)"
        return snap

    before = daily[_dates(daily) < session.date]
    if before.empty:
        snap.error = "No previous close to compare against"
        return snap
    snap.prev_close = float(before["Close"].iloc[-1])

    volumes = before["Volume"].tail(lookback_days)
    volumes = volumes[volumes > 0]
    if len(volumes) >= MIN_VOLUME_DAYS:
        snap.avg_volume = float(volumes.mean())

    bars_today = None
    if intraday is not None and not intraday.empty:
        bars_today = intraday[_dates(intraday) == session.date]

    if session.phase == PRE:
        if bars_today is None or bars_today.empty:
            return snap  # nothing has traded yet this morning
        pre = bars_today[bars_today.index.time < MARKET_OPEN]
        if pre.empty:
            return snap
        snap.price = float(pre["Close"].iloc[-1])
        snap.as_of = pre.index[-1].to_pydatetime()
        snap.change_pct = (snap.price / snap.prev_close - 1) * 100
        snap.gap_pct = snap.change_pct
        # Yahoo reports zero volume on pre-market bars, so leave it unknown rather than show 0.
        pre_volume = int(pre["Volume"].sum())
        snap.volume = pre_volume or None
        return snap

    day = daily[_dates(daily) == session.date]
    if day.empty:
        return snap  # no regular-session trade yet (just opened, or halted)
    row = day.iloc[-1]
    snap.price = float(row["Close"])
    snap.change_pct = (snap.price / snap.prev_close - 1) * 100
    if pd.notna(row["Open"]) and row["Open"] > 0:
        snap.gap_pct = (float(row["Open"]) / snap.prev_close - 1) * 100
    if pd.notna(row["Volume"]) and row["Volume"] > 0:
        snap.volume = int(row["Volume"])
    if bars_today is not None and not bars_today.empty:
        regular_today = _regular_hours(bars_today)
        if not regular_today.empty:
            snap.as_of = regular_today.index[-1].to_pydatetime()

    if not (snap.volume and snap.avg_volume):
        return snap
    if session.phase != REGULAR:
        snap.rel_volume = snap.volume / snap.avg_volume
    elif intraday is not None and not intraday.empty:
        # Today's running total comes from the daily bar: Yahoo's intraday bars for the
        # current day carry stray prints that can multiply the sum several times over.
        share = usual_share_of_day(intraday, daily, session.date, now, lookback_days)
        if share:
            snap.rel_volume = snap.volume / (snap.avg_volume * share)
    return snap
