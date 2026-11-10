from __future__ import annotations

import json
from typing import TYPE_CHECKING

from scanner.analyzer import ScanResult
from scanner.metrics import CLOSED, ET, PRE, REGULAR

if TYPE_CHECKING:
    from scanner.agent import Scan


def _format_price(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "—"


def _format_pct(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def _round(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


def _move_size(result: ScanResult) -> float:
    return abs(result.snapshot.change_pct or 0.0)


def _headline(scan: Scan) -> str:
    when = scan.scanned_at.astimezone(ET).strftime("%Y-%m-%d %H:%M ET")
    if scan.session.phase == CLOSED:
        return f"Stock Watchlist Scan — {when} — market closed, showing {scan.session.date:%a %b %d}"
    return f"Stock Watchlist Scan — {when} — {scan.session.phase}"


def render_table(scan: Scan, show_all: bool) -> str:
    results = scan.results
    phase = scan.session.phase
    lines: list[str] = [_headline(scan), ""]

    failed = [r for r in results if r.snapshot.error]
    flagged = sorted((r for r in results if r.has_alerts), key=_move_size, reverse=True)
    display = [r for r in results if not r.snapshot.error]
    if not show_all:
        display = flagged

    if flagged:
        lines.append(f"ALERTS ({len(flagged)})")
        lines.append("-" * 60)
        for result in flagged:
            for alert in result.alerts:
                lines.append(f"  {alert.symbol}: {alert.reason}")
            for item in result.headlines:
                lines.append(f"      {item.published}  {item.title} ({item.source})")
        lines.append("")
    else:
        lines.append("No alerts.")
        lines.append("")

    if display:
        volume_label = "Vol vs avg" if phase != REGULAR else "Vol vs usual"
        header = (
            f"{'Symbol':<8} {'Name':<18} {'Price':>10} {'Prev close':>11} {'Change':>9} "
            f"{'Open gap':>9} {'Volume':>13} {volume_label:>12}"
        )
        lines.append(header)
        lines.append("-" * len(header))
        for result in display:
            s = result.snapshot
            marker = " *" if result.has_alerts else ""
            gap = "—" if phase == PRE else _format_pct(s.gap_pct)
            vol = f"{s.volume:,}" if s.volume else "—"
            ratio = f"{s.rel_volume:.2f}x" if s.rel_volume is not None else "—"
            lines.append(
                f"{s.symbol:<8} {s.name[:18]:<18} {_format_price(s.price):>10} "
                f"{_format_price(s.prev_close):>11} {_format_pct(s.change_pct):>9} "
                f"{gap:>9} {vol:>13} {ratio:>12}{marker}"
            )
        lines.append("")
        lines.append("* = triggered an alert")
        if phase == PRE:
            lines.append(
                "Change is the pre-market price against yesterday's close. Yahoo doesn't report "
                "pre-market volume, so volume alerts start at the open."
            )
        elif phase == REGULAR:
            lines.append("Vol vs usual compares volume so far with the same time on earlier days.")

    if failed:
        lines.append("")
        lines.append(f"COULD NOT SCAN ({len(failed)})")
        for result in failed:
            lines.append(f"  {result.snapshot.symbol}: {result.snapshot.error}")

    return "\n".join(lines)


def render_json(scan: Scan) -> str:
    results = scan.results
    payload = {
        "scanned_at": scan.scanned_at.isoformat(),
        "session": scan.session.phase,
        "session_date": scan.session.date.isoformat(),
        "total": len(results),
        "alert_count": sum(1 for r in results if r.has_alerts),
        "error_count": sum(1 for r in results if r.snapshot.error),
        "stocks": [
            {
                "symbol": r.snapshot.symbol,
                "name": r.snapshot.name,
                "price": _round(r.snapshot.price),
                "prev_close": _round(r.snapshot.prev_close),
                "change_pct": _round(r.snapshot.change_pct),
                "gap_pct": _round(r.snapshot.gap_pct),
                "volume": r.snapshot.volume,
                "avg_volume": _round(r.snapshot.avg_volume, 0),
                "volume_ratio": _round(r.snapshot.rel_volume),
                "as_of": r.snapshot.as_of.isoformat() if r.snapshot.as_of else None,
                "alerts": [{"symbol": a.symbol, "reason": a.reason} for a in r.alerts],
                "headlines": [
                    {"published": h.published, "title": h.title, "source": h.source}
                    for h in r.headlines
                ],
                "error": r.snapshot.error,
            }
            for r in results
        ],
    }
    return json.dumps(payload, indent=2)
