"""Real NASA data: DONKI space-weather events (api.nasa.gov/DONKI/FLR).

Solar flares are real physical events that raise astronaut radiation exposure.
We fetch real flare records and turn them into a daily risk multiplier that
drives the simulated radiation_msv_day indicator -- so the one indicator that
most directly threatens crew health is anchored in an actual NASA feed, not
a made-up number.

Network may not be available (offline demo, no internet during judging, rate
limit). In that case we fall back to a small bundled sample so the dashboard
still runs -- the UI always says clearly which mode it is in.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

DONKI_URL = "https://api.nasa.gov/DONKI/FLR"
FALLBACK_PATH = Path(__file__).parent.parent / "data" / "donki_flr_sample.json"

# NASA flare class -> rough relative intensity, used only to weight the risk
# multiplier. Letter classes are logarithmic: X > M > C > B > A.
CLASS_WEIGHT = {"X": 1.0, "M": 0.5, "C": 0.15, "B": 0.03, "A": 0.01}


@dataclass
class FlareDaySummary:
    day: date
    flare_count: int
    max_class: str
    risk_multiplier: float  # 1.0 = quiet sun, >1.0 = elevated radiation risk


def _class_weight(class_type: str) -> float:
    if not class_type:
        return 0.0
    return CLASS_WEIGHT.get(class_type[0].upper(), 0.0)


def fetch_flares(start: date, end: date, api_key: Optional[str] = None,
                 timeout: int = 6) -> tuple[list[dict], str]:
    """Return (records, mode). mode is 'live' or 'offline-fallback'."""
    key = api_key or os.environ.get("NASA_API_KEY", "DEMO_KEY")
    url = f"{DONKI_URL}?startDate={start.isoformat()}&endDate={end.isoformat()}&api_key={key}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), "live"
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        if FALLBACK_PATH.exists():
            return json.loads(FALLBACK_PATH.read_text()), "offline-fallback"
        return [], "offline-fallback"


def summarize_by_day(records: list[dict], start: date, end: date) -> dict[date, FlareDaySummary]:
    """One summary per calendar day in [start, end], even on days with no flares."""
    by_day: dict[date, list[dict]] = {}
    for rec in records:
        begin = rec.get("beginTime") or rec.get("peakTime")
        if not begin:
            continue
        d = datetime.fromisoformat(begin.replace("Z", "+00:00")).date()
        by_day.setdefault(d, []).append(rec)

    out: dict[date, FlareDaySummary] = {}
    cur = start
    while cur <= end:
        day_recs = by_day.get(cur, [])
        if day_recs:
            weights = [_class_weight(r.get("classType", "")) for r in day_recs]
            max_rec = max(day_recs, key=lambda r: _class_weight(r.get("classType", "")))
            risk = 1.0 + 3.0 * max(weights)  # one strong flare dominates the day's risk
            out[cur] = FlareDaySummary(cur, len(day_recs), max_rec.get("classType", "-"), round(risk, 2))
        else:
            out[cur] = FlareDaySummary(cur, 0, "-", 1.0)
        cur += timedelta(days=1)
    return out


def mission_risk_series(n_days: int, mission_start: date, api_key: Optional[str] = None
                        ) -> tuple[list[FlareDaySummary], str]:
    """Convenience wrapper: real flare-derived risk for each day of the mission.

    Uses the most recent n_days of actual DONKI history as a stand-in for "what
    the sun is doing right now", since we cannot fetch future solar activity.
    """
    end = date.today()
    start = end - timedelta(days=n_days - 1)
    records, mode = fetch_flares(start, end, api_key)
    by_day = summarize_by_day(records, start, end)
    series = [by_day[d] for d in sorted(by_day)]
    series = [FlareDaySummary(mission_start + timedelta(days=i), s.flare_count, s.max_class,
                              s.risk_multiplier) for i, s in enumerate(series)]
    return series, mode
