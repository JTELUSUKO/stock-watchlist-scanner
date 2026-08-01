from __future__ import annotations

import json
from datetime import datetime, timezone

from scanner.analyzer import ScanResult


def _format_price(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "—"


def _format_pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def render_table(results: list[ScanResult], show_all: bool) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"Stock Watchlist Scan — {now}")
    lines.append("")

    flagged = [r for r in results if r.has_alerts]
    display = results if show_all else flagged

    if flagged:
        lines.append(f"ALERTS ({len(flagged)})")
        lines.append("-" * 60)
        for result in flagged:
            for alert in result.alerts:
                lines.append(f"  {alert.symbol}: {alert.reason}")
        lines.append("")

    if not display:
        lines.append("No stocks to display.")
        return "\n".join(lines)

    header = f"{'Symbol':<8} {'Name':<18} {'Price':>10} {'Change':>9} {'Volume':>12} {'Vol Ratio':>10}"
    lines.append(header)
    lines.append("-" * len(header))

    for result in display:
        s = result.snapshot
        marker = " *" if result.has_alerts else ""
        vol = f"{s.volume:,}" if s.volume else "—"
        ratio = f"{s.volume_ratio:.2f}x" if s.volume_ratio else "—"
        lines.append(
            f"{s.symbol:<8} {s.name[:18]:<18} {_format_price(s.price):>10} "
            f"{_format_pct(s.change_pct):>9} {vol:>12} {ratio:>10}{marker}"
        )

    lines.append("")
    lines.append("* = triggered an alert")
    return "\n".join(lines)


def render_json(results: list[ScanResult]) -> str:
    payload = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "alert_count": sum(1 for r in results if r.has_alerts),
        "stocks": [
            {
                "symbol": r.snapshot.symbol,
                "name": r.snapshot.name,
                "price": r.snapshot.price,
                "change_pct": r.snapshot.change_pct,
                "volume": r.snapshot.volume,
                "volume_ratio": r.snapshot.volume_ratio,
                "alerts": [{"symbol": a.symbol, "reason": a.reason} for a in r.alerts],
                "error": r.snapshot.error,
            }
            for r in results
        ],
    }
    return json.dumps(payload, indent=2)
