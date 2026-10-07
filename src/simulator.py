"""Synthetic astronaut vitals. ALL VALUES ARE SIMULATED, not real crew data.

Replace or extend with NASA open data once the 2026 challenge statement lists
its datasets (candidate: NASA OSDR).
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

MISSION_START = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def generate_readings(n_days: int = 30, seed: int = 42, scenario: str = "nominal",
                      radiation_risk=None):
    """Return a list of (iso_timestamp, data_dict), one reading per mission day.

    scenario="declining" drifts sleep, heart rate, activity and stress the wrong
    way over the last ~40% of the mission so the dashboard has something to flag.

    radiation_risk: optional list of per-day risk multipliers from
    nasa_loader.mission_risk_series(), derived from REAL NASA DONKI solar-flare
    data. When given, radiation_msv_day is the simulated baseline dose scaled by
    that day's real solar activity, instead of being purely synthetic.
    """
    rng = random.Random(seed)
    onset = int(n_days * 0.6)
    out = []
    for d in range(n_days):
        drift = 0.0
        if scenario == "declining" and d >= onset:
            drift = min(1.0, (d - onset + 1) / max(1, n_days - onset))
        base_dose = max(0.1, rng.gauss(0.55, 0.05) + 0.8 * drift)
        risk_mult = radiation_risk[d].risk_multiplier if radiation_risk and d < len(radiation_risk) else 1.0
        data = {
            "sleep_hours": round(max(3.0, rng.gauss(7.0, 0.4) - 2.4 * drift), 1),
            "resting_hr": int(round(rng.gauss(62, 2.5) + 30 * drift)),
            "activity_min": int(round(max(5, rng.gauss(120, 12) - 80 * drift))),
            "stress_1_10": int(max(1, min(10, round(rng.gauss(3, 1) + 5 * drift)))),
            "radiation_msv_day": round(base_dose * risk_mult, 2),
            "source": "simulated+donki" if radiation_risk else "simulated",
        }
        ts = (MISSION_START + timedelta(days=d)).isoformat(timespec="seconds")
        out.append((ts, data))
    return out
