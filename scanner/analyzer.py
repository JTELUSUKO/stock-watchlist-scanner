from __future__ import annotations

from dataclasses import dataclass, field

from scanner.metrics import PRE, StockSnapshot


@dataclass
class Alert:
    symbol: str
    reason: str


@dataclass
class Headline:
    published: str
    title: str
    source: str


@dataclass
class ScanResult:
    snapshot: StockSnapshot
    alerts: list[Alert] = field(default_factory=list)
    headlines: list[Headline] = field(default_factory=list)

    @property
    def has_alerts(self) -> bool:
        return len(self.alerts) > 0


def analyze_snapshot(
    snapshot: StockSnapshot,
    price_change_threshold: float,
    volume_spike_ratio: float,
    phase: str,
) -> ScanResult:
    """Flag a stock whose move or volume crosses a threshold. A failed fetch is not an alert."""
    alerts: list[Alert] = []
    if snapshot.error:
        return ScanResult(snapshot=snapshot)

    change = snapshot.change_pct
    if change is not None and abs(change) >= price_change_threshold:
        direction = "up" if change > 0 else "down"
        what = "Pre-market gap" if phase == PRE else "Price moved"
        alerts.append(
            Alert(
                snapshot.symbol,
                f"{what} {direction} {abs(change):.2f}% (threshold: {price_change_threshold:g}%)",
            )
        )

    if snapshot.rel_volume is not None and snapshot.rel_volume >= volume_spike_ratio:
        alerts.append(
            Alert(
                snapshot.symbol,
                f"Volume {snapshot.rel_volume:.2f}x normal (threshold: {volume_spike_ratio:g}x)",
            )
        )

    return ScanResult(snapshot=snapshot, alerts=alerts)
