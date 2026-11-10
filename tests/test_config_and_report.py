from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from scanner.agent import Scan
from scanner.analyzer import analyze_snapshot
from scanner.config import ConfigError, load_config, load_watchlist
from scanner.fetcher import yahoo_symbol
from scanner.metrics import PRE, REGULAR, Session, StockSnapshot
from scanner.report import render_json, render_table


def make_scan(phase: str) -> Scan:
    snaps = [
        StockSnapshot("AAA", "Alpha", price=105.0, prev_close=100.0, change_pct=5.0),
        StockSnapshot("BBB", "Beta", price=50.0, prev_close=50.1, change_pct=-0.2),
        StockSnapshot("ZZZ", "Broken", error="No price data from Yahoo (check the symbol)"),
    ]
    return Scan(
        scanned_at=datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc),
        session=Session(phase, date(2026, 11, 10)),
        results=[analyze_snapshot(s, 2.0, 1.5, phase) for s in snaps],
    )


def test_table_shows_eastern_time_alerts_and_failures_separately():
    text = render_table(make_scan(PRE), show_all=True)
    assert "2026-11-10 09:00 ET — pre-market" in text
    assert "ALERTS (1)" in text
    assert "AAA: Pre-market gap up 5.00%" in text
    assert "COULD NOT SCAN (1)" in text
    assert "ZZZ: No price data" in text


def test_alerts_only_table_hides_quiet_stocks():
    text = render_table(make_scan(REGULAR), show_all=False)
    assert "Alpha" in text and "Beta" not in text


def test_json_counts_errors_apart_from_alerts():
    payload = json.loads(render_json(make_scan(REGULAR)))
    assert (payload["total"], payload["alert_count"], payload["error_count"]) == (3, 1, 1)
    assert payload["session"] == "regular"


def test_config_defaults_when_file_is_missing(tmp_path):
    assert load_config(tmp_path / "none.yaml").price_change_pct == 2.0


def test_config_rejects_a_bad_threshold(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("alerts:\n  price_change_pct: -1\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_watchlist_upper_cases_and_drops_duplicates(tmp_path):
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps({"stocks": [{"symbol": "aapl", "name": "Apple"}, "AAPL", "brk.b"]}))
    assert load_watchlist(path) == [("AAPL", "Apple"), ("BRK.B", "BRK.B")]
    assert yahoo_symbol("BRK.B") == "BRK-B"


def test_watchlist_without_stocks_is_rejected(tmp_path):
    path = tmp_path / "watchlist.json"
    path.write_text("{}")
    with pytest.raises(ConfigError):
        load_watchlist(path)
