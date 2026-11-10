from __future__ import annotations

from scanner.analyzer import analyze_snapshot
from scanner.metrics import PRE, REGULAR, StockSnapshot


def snap(**fields) -> StockSnapshot:
    return StockSnapshot(symbol="A", name="A", **fields)


def test_move_at_the_threshold_is_flagged_in_both_directions():
    assert analyze_snapshot(snap(change_pct=2.0), 2.0, 1.5, REGULAR).has_alerts
    assert analyze_snapshot(snap(change_pct=-2.0), 2.0, 1.5, REGULAR).has_alerts
    assert not analyze_snapshot(snap(change_pct=1.99), 2.0, 1.5, REGULAR).has_alerts


def test_pre_market_move_is_called_a_gap():
    result = analyze_snapshot(snap(change_pct=-3.5), 2.0, 1.5, PRE)
    assert result.alerts[0].reason.startswith("Pre-market gap down 3.50%")


def test_volume_spike_is_flagged():
    result = analyze_snapshot(snap(change_pct=0.1, rel_volume=1.5), 2.0, 1.5, REGULAR)
    assert [a.reason for a in result.alerts] == ["Volume 1.50x normal (threshold: 1.5x)"]


def test_failed_fetch_is_not_an_alert():
    result = analyze_snapshot(snap(error="No price data"), 2.0, 1.5, REGULAR)
    assert not result.has_alerts
