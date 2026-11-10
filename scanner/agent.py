from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from scanner.analyzer import ScanResult, analyze_snapshot
from scanner.config import Config, load_config, load_watchlist
from scanner.fetcher import fetch_market_data
from scanner.metrics import Session, build_snapshot, detect_session
from scanner.news import recent_headlines
from scanner.report import render_json, render_table


@dataclass
class Scan:
    scanned_at: datetime
    session: Session
    results: list[ScanResult]

    @property
    def all_failed(self) -> bool:
        return all(r.snapshot.error for r in self.results)


class WatchlistScannerAgent:
    """Scans a configured watchlist and flags notable price/volume moves."""

    def __init__(
        self,
        project_root: Path | None = None,
        watchlist_path: Path | None = None,
        config_path: Path | None = None,
    ):
        self.root = project_root or Path(__file__).resolve().parent.parent
        self.watchlist_path = watchlist_path or self.root / "watchlist.json"
        self.config_path = config_path or self.root / "config.yaml"

    def scan(self, config: Config | None = None, now: datetime | None = None) -> Scan:
        config = config or load_config(self.config_path)
        stocks = load_watchlist(self.watchlist_path)
        now = now or datetime.now(timezone.utc)

        data = fetch_market_data([symbol for symbol, _ in stocks])
        session = detect_session(now, data.intraday)

        results: list[ScanResult] = []
        for symbol, name in stocks:
            snapshot = build_snapshot(
                symbol,
                name,
                data.daily.get(symbol),
                data.intraday.get(symbol),
                session,
                now,
                lookback_days=config.lookback_days,
            )
            result = analyze_snapshot(
                snapshot, config.price_change_pct, config.volume_spike_ratio, session.phase
            )
            if result.has_alerts and config.news_enabled:
                result.headlines = recent_headlines(symbol, config.news_max_headlines, now)
            results.append(result)
        return Scan(scanned_at=now, session=session, results=results)

    def run(self, output_format: str | None = None) -> tuple[str, bool]:
        """Return the rendered report and whether the scan got any data at all."""
        config = load_config(self.config_path)
        scan = self.scan(config)
        if (output_format or config.output_format) == "json":
            return render_json(scan), not scan.all_failed
        return render_table(scan, show_all=config.show_all), not scan.all_failed
