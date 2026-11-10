#!/usr/bin/env python3
"""Run the stock watchlist scanner agent."""

import argparse
import sys
import warnings
from pathlib import Path

# The macOS system Python links LibreSSL, which makes urllib3 warn on every run.
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from scanner.agent import WatchlistScannerAgent  # noqa: E402
from scanner.config import ConfigError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan your stock watchlist for price moves and volume spikes."
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=None,
        help="Path to watchlist JSON (default: watchlist.json)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config YAML (default: config.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    agent = WatchlistScannerAgent(
        watchlist_path=args.watchlist,
        config_path=args.config,
    )

    try:
        report, got_data = agent.run(output_format="json" if args.json else None)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(report)
    return 0 if got_data else 1


if __name__ == "__main__":
    sys.exit(main())
