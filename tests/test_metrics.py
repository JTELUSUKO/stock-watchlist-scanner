from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from scanner.metrics import (
    CLOSED,
    ET,
    POST,
    PRE,
    REGULAR,
    Session,
    build_snapshot,
    detect_session,
    usual_share_of_day,
)

TODAY = date(2026, 11, 10)  # a Tuesday


def et(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ET)


def daily_frame(rows: list[tuple[date, float, float, int]]) -> pd.DataFrame:
    index = pd.DatetimeIndex([pd.Timestamp(d) for d, *_ in rows])
    return pd.DataFrame(
        {
            "Open": [o for _, o, _, _ in rows],
            "Close": [c for _, _, c, _ in rows],
            "Volume": [v for _, _, _, v in rows],
        },
        index=index,
    )


def bars(rows: list[tuple[datetime, float, int]]) -> pd.DataFrame:
    index = pd.DatetimeIndex([ts for ts, _, _ in rows])
    return pd.DataFrame(
        {"Close": [c for _, c, _ in rows], "Volume": [v for _, _, v in rows]}, index=index
    )


def prior_days(count: int) -> list[date]:
    days = pd.bdate_range(end=pd.Timestamp(TODAY) - pd.Timedelta(days=1), periods=count)
    return [d.date() for d in days]


def history(count: int = 10, close: float = 100.0, volume: int = 1_000_000):
    """Earlier days that each trade a quarter of their volume in the first half hour."""
    days = prior_days(count)
    daily = [(d, close, close, volume) for d in days]
    intraday = []
    for d in days:
        intraday.append((et(d, 9, 30), close, volume // 4))
        intraday.append((et(d, 12, 0), close, volume // 4))
        intraday.append((et(d, 15, 55), close, volume // 4))  # the rest is the closing auction
    return daily, intraday


def test_session_is_pre_market_before_the_open():
    intraday = {"A": bars([(et(TODAY, 8, 0), 100, 0)])}
    assert detect_session(et(TODAY, 9, 0), intraday) == Session(PRE, TODAY)


def test_session_is_regular_then_after_hours():
    intraday = {"A": bars([(et(TODAY, 9, 30), 100, 10)])}
    assert detect_session(et(TODAY, 9, 30), intraday).phase == REGULAR
    assert detect_session(et(TODAY, 16, 0), intraday).phase == POST


def test_session_is_closed_on_a_day_without_bars():
    friday = date(2026, 11, 6)
    intraday = {"A": bars([(et(friday, 15, 55), 100, 10)])}
    saturday_noon = et(date(2026, 11, 7), 12)
    assert detect_session(saturday_noon, intraday) == Session(CLOSED, friday)


def test_pre_market_change_is_against_yesterdays_close():
    daily, intraday = history(close=100.0)
    intraday += [(et(TODAY, 8, 0), 103.0, 0), (et(TODAY, 9, 0), 105.0, 0)]
    snap = build_snapshot(
        "A", "A", daily_frame(daily), bars(intraday), Session(PRE, TODAY), et(TODAY, 9, 5)
    )
    assert snap.prev_close == 100.0
    assert snap.price == 105.0
    assert snap.change_pct == pytest.approx(5.0)
    assert snap.volume is None  # Yahoo's zero is "unknown", not "none traded"
    assert snap.rel_volume is None


def test_pre_market_without_trades_keeps_the_previous_close_only():
    daily, intraday = history()
    snap = build_snapshot(
        "A", "A", daily_frame(daily), bars(intraday), Session(PRE, TODAY), et(TODAY, 7, 0)
    )
    assert snap.error is None
    assert snap.prev_close == 100.0
    assert snap.price is None and snap.change_pct is None


def test_regular_hours_use_the_previous_day_not_two_days_back():
    daily, intraday = history(close=100.0)
    daily[-2] = (daily[-2][0], 50.0, 50.0, 1_000_000)  # the day before yesterday
    daily.append((TODAY, 102.0, 104.0, 500_000))
    intraday.append((et(TODAY, 9, 30), 104.0, 500_000))
    snap = build_snapshot(
        "A", "A", daily_frame(daily), bars(intraday), Session(REGULAR, TODAY), et(TODAY, 9, 35)
    )
    assert snap.prev_close == 100.0
    assert snap.change_pct == pytest.approx(4.0)
    assert snap.gap_pct == pytest.approx(2.0)


def test_relative_volume_compares_with_the_same_time_of_day():
    daily, intraday = history(volume=1_000_000)
    # By 09:35 a quarter of a normal day (250k) has usually traded. Today: 500k.
    daily.append((TODAY, 100.0, 100.0, 500_000))
    intraday.append((et(TODAY, 9, 30), 100.0, 500_000))
    snap = build_snapshot(
        "A", "A", daily_frame(daily), bars(intraday), Session(REGULAR, TODAY), et(TODAY, 9, 35)
    )
    assert snap.rel_volume == pytest.approx(2.0)


def test_relative_volume_ignores_a_bad_intraday_print_today():
    daily, intraday = history(volume=1_000_000)
    daily.append((TODAY, 100.0, 100.0, 250_000))
    intraday.append((et(TODAY, 9, 30), 100.0, 90_000_000))  # stray print in the 5-minute bar
    snap = build_snapshot(
        "A", "A", daily_frame(daily), bars(intraday), Session(REGULAR, TODAY), et(TODAY, 9, 35)
    )
    assert snap.rel_volume == pytest.approx(1.0)


def test_usual_share_counts_the_unfinished_bar_by_time_elapsed():
    daily, intraday = history(volume=1_000_000)
    share = usual_share_of_day(bars(intraday), daily_frame(daily), TODAY, et(TODAY, 9, 32, ), 20)
    assert share == pytest.approx(0.25 * 2 / 5)


def test_relative_volume_needs_enough_history():
    daily, intraday = history(count=3)
    daily.append((TODAY, 100.0, 100.0, 500_000))
    intraday.append((et(TODAY, 9, 30), 100.0, 500_000))
    snap = build_snapshot(
        "A", "A", daily_frame(daily), bars(intraday), Session(REGULAR, TODAY), et(TODAY, 9, 35)
    )
    assert snap.rel_volume is None
    assert snap.change_pct == pytest.approx(0.0)


def test_after_the_close_volume_is_against_the_average_without_today():
    daily, intraday = history(volume=1_000_000)
    daily.append((TODAY, 100.0, 97.0, 3_000_000))
    intraday.append((et(TODAY, 15, 55), 97.0, 1_000))
    snap = build_snapshot(
        "A", "A", daily_frame(daily), bars(intraday), Session(POST, TODAY), et(TODAY, 17, 0)
    )
    assert snap.avg_volume == pytest.approx(1_000_000)
    assert snap.rel_volume == pytest.approx(3.0)
    assert snap.change_pct == pytest.approx(-3.0)


def test_missing_data_is_an_error_not_a_crash():
    snap = build_snapshot("ZZZZ", "Nope", None, None, Session(REGULAR, TODAY), et(TODAY, 10, 0))
    assert snap.error
