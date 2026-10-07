"""Traffic-light status from recent readings.

Thresholds are ILLUSTRATIVE for the demo. This shows indicators and trends; it
is not a medical diagnosis.
"""
from __future__ import annotations

from dataclasses import dataclass

LEVELS = ["green", "yellow", "red"]

RULES = {
    "sleep_hours": dict(label="Sleep", unit="h", bad="low", yellow=6.5, red=5.5,
                        advice="Sleep has been below target. Protect a full rest period and review your schedule."),
    "resting_hr": dict(label="Resting heart rate", unit="bpm", bad="high", yellow=75, red=90,
                       advice="Resting heart rate is elevated. Rest, hydrate, and re-measure at the same time tomorrow."),
    "activity_min": dict(label="Exercise", unit="min", bad="low", yellow=90, red=60,
                         advice="Exercise time is low. Countermeasure exercise protects bone and muscle, so make time for it."),
    "stress_1_10": dict(label="Stress", unit="/10", bad="high", yellow=5.5, red=7.5,
                        advice="Stress is trending high. Take a break, talk with the crew, and log how you feel."),
    "radiation_msv_day": dict(label="Radiation (est.)", unit="mSv/day", bad="high", yellow=0.8, red=1.2,
                              advice="Estimated radiation dose is high. Move to the more shielded area of the habitat if procedure allows."),
}


@dataclass
class IndicatorStatus:
    key: str
    label: str
    value: float
    unit: str
    level: str
    advice: str  # empty when green


@dataclass
class Assessment:
    overall: str
    indicators: list
    window: int


def _level(value: float, rule: dict) -> str:
    if rule["bad"] == "low":
        if value < rule["red"]:
            return "red"
        if value < rule["yellow"]:
            return "yellow"
    else:
        if value > rule["red"]:
            return "red"
        if value > rule["yellow"]:
            return "yellow"
    return "green"


def evaluate(readings: list[dict], window: int = 3) -> Assessment:
    """Average the last `window` readings per indicator (smooths one-off noise)."""
    recent = readings[-window:]
    indicators = []
    for key, rule in RULES.items():
        vals = [r[key] for r in recent if key in r]
        if not vals:
            continue
        avg = round(sum(vals) / len(vals), 2)
        lvl = _level(avg, rule)
        indicators.append(IndicatorStatus(key, rule["label"], avg, rule["unit"], lvl,
                                          rule["advice"] if lvl != "green" else ""))
    overall = max((i.level for i in indicators), key=LEVELS.index, default="green")
    return Assessment(overall, indicators, len(recent))
