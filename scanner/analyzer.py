from __future__ import annotations

from dataclasses import dataclass, field

from scanner.fetcher import StockSnapshot


@dataclass
class Alert:
    symbol: str
    reason: str


@dataclass
class ScanResult:
    snapshot: StockSnapshot
    alerts: list[Alert] = field(default_factory=list)

    @property
    def has_alerts(self) -> bool:
        return len(self.alerts) > 0


def analyze_snapshot(
    snapshot: StockSnapshot,
    price_change_threshold: float,
    volume_spike_ratio: float,
) -> ScanResult:
    alerts: list[Alert] = []

    if snapshot.error:
        alerts.append(Alert(snapshot.symbol, f"Fetch failed: {snapshot.error}"))
        return ScanResult(snapshot=snapshot, alerts=alerts)

    if snapshot.change_pct is not None and abs(snapshot.change_pct) >= price_change_threshold:
        direction = "up" if snapshot.change_pct > 0 else "down"
        alerts.append(
            Alert(
                snapshot.symbol,
                f"Price moved {direction} {abs(snapshot.change_pct):.2f}% (threshold: {price_change_threshold}%)",
            )
        )

    if snapshot.volume_ratio is not None and snapshot.volume_ratio >= volume_spike_ratio:
        alerts.append(
            Alert(
                snapshot.symbol,
                f"Volume spike {snapshot.volume_ratio:.2f}x average (threshold: {volume_spike_ratio}x)",
            )
        )

    return ScanResult(snapshot=snapshot, alerts=alerts)
