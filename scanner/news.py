"""Recent headlines for flagged stocks, from Finviz. Optional: a scan never fails over news."""

from __future__ import annotations

from datetime import datetime, timedelta

from scanner.analyzer import Headline
from scanner.metrics import ET

MAX_AGE = timedelta(days=2)


def recent_headlines(symbol: str, limit: int, now: datetime) -> list[Headline]:
    try:
        from finvizfinance.quote import finvizfinance

        news = finvizfinance(symbol.replace(".", "-")).ticker_news()
    except Exception:
        return []

    # Finviz stamps headlines in Eastern time without a zone, newest first.
    current = now.astimezone(ET).replace(tzinfo=None)
    headlines: list[Headline] = []
    try:
        for row in news.itertuples():
            if len(headlines) >= limit:
                break
            # Skip rows the parser put on the wrong day (they show up in the future).
            if not (current - MAX_AGE <= row.Date <= current + timedelta(minutes=5)):
                continue
            headlines.append(
                Headline(
                    published=row.Date.strftime("%b %d %H:%M"),
                    title=" ".join(str(row.Title).split()),
                    source=str(row.Source),
                )
            )
    except Exception:
        return headlines
    return headlines
