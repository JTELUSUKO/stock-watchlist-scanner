from __future__ import annotations

import json
from pathlib import Path

import yaml

from scanner.analyzer import ScanResult, analyze_snapshot
from scanner.fetcher import fetch_snapshot
from scanner.report import render_json, render_table


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

    def load_watchlist(self) -> list[dict]:
        data = json.loads(self.watchlist_path.read_text())
        return data.get("stocks", [])

    def load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        return yaml.safe_load(self.config_path.read_text()) or {}

    def scan(self) -> list[ScanResult]:
        config = self.load_config()
        alerts_cfg = config.get("alerts", {})
        scan_cfg = config.get("scan", {})

        price_threshold = float(alerts_cfg.get("price_change_pct", 2.0))
        volume_threshold = float(alerts_cfg.get("volume_spike_ratio", 1.5))
        period = scan_cfg.get("period", "1mo")

        results: list[ScanResult] = []
        for entry in self.load_watchlist():
            symbol = entry["symbol"].upper()
            name = entry.get("name", symbol)
            snapshot = fetch_snapshot(symbol, name, period=period)
            results.append(
                analyze_snapshot(snapshot, price_threshold, volume_threshold)
            )
        return results

    def run(self, output_format: str | None = None) -> str:
        config = self.load_config()
        output_cfg = config.get("output", {})
        fmt = output_format or output_cfg.get("format", "table")
        results = self.scan()

        if fmt == "json":
            return render_json(results)
        return render_table(results, show_all=output_cfg.get("show_all", True))
