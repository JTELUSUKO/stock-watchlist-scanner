#!/usr/bin/env python3
"""Run the stock watchlist scanner agent."""

import argparse
from pathlib import Path

from scanner.agent import WatchlistScannerAgent


def main() -> None:
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

    output_format = "json" if args.json else None
    print(agent.run(output_format=output_format))


if __name__ == "__main__":
    main()
