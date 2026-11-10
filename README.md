# Stock watchlist scanner

Scans a watchlist before and during the US trading day and flags stocks with a large price move or unusual volume.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py            # table
.venv/bin/python run.py --json     # JSON
```

Edit `watchlist.json` for the stocks and `config.yaml` for the thresholds.

## What it reports

The scan works out the session from the clock and the data (Eastern time), so weekends and holidays show the last
trading day instead of stale "today" figures.

| When | Change | Volume |
| --- | --- | --- |
| Pre-market (04:00–09:30 ET) | Latest pre-market price against yesterday's close | Not available: Yahoo reports no pre-market volume |
| Regular hours | Latest price against yesterday's close, plus the gap at the open | Volume so far against what has usually traded by this time of day |
| After the close, weekends, holidays | Close against the previous close | The day's volume against the 20-day average |

Flagged stocks get their latest Finviz headline (turn off with `news.enabled: false`).

Prices and volume come from Yahoo Finance through `yfinance`; headlines from Finviz through `finvizfinance`. Both are
unofficial and can be delayed or missing. A stock that couldn't be fetched is listed under "COULD NOT SCAN", and the
command exits with 1 when nothing could be fetched.

## Run it every weekday morning (macOS)

```
scripts/install-schedule.sh          # 09:00 local time
scripts/install-schedule.sh 08:45    # or pick a time
```

The time is the Mac's local time, so outside the Eastern time zone choose the local equivalent of the pre-market time
you want. Reports are appended to `logs/scanner.log`. Keep the project out of Desktop, Documents and Downloads: macOS
blocks scheduled jobs from reading those folders.

## Tests

```
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```
