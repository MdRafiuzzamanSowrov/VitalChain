from src import demo_attacks
from src.chain import HealthLog
from src.simulator import generate_readings
from src.status import evaluate

KEY = b"k" * 32


def build(key=KEY, n=10, scenario="nominal"):
    log = HealthLog(key)
    for ts, data in generate_readings(n, scenario=scenario):
        log.append(data, ts)
    return log


def test_intact_log_verifies():
    res = build().verify()
    assert res.ok and res.checked == 10


def test_edit_is_detected_at_the_right_record():
    log = build()
    demo_attacks.edit(log, 4, "sleep_hours", 9.9)
    res = log.verify()
    assert not res.ok and res.bad_index == 4


def test_delete_in_the_middle_is_detected():
    log = build()
    demo_attacks.delete(log, 3)
    assert not log.verify().ok


def test_forged_rehash_fails_with_device_key():
    log = build(key=KEY)
    demo_attacks.forge(log, 4, "sleep_hours", 9.9)
    assert not log.verify().ok


def test_forged_rehash_succeeds_without_key():
    """Documents WHY the HMAC key matters: a plain hash chain can be rewritten."""
    log = build(key=None)
    demo_attacks.forge(log, 4, "sleep_hours", 9.9)
    assert log.verify().ok


def test_save_load_roundtrip(tmp_path):
    log = build()
    p = tmp_path / "log.jsonl"
    log.save(p)
    loaded = HealthLog.load(p, KEY)
    assert loaded.verify().ok and loaded.head() == log.head()


def test_wrong_key_fails_verification(tmp_path):
    log = build()
    p = tmp_path / "log.jsonl"
    log.save(p)
    assert not HealthLog.load(p, b"x" * 32).verify().ok


def test_status_nominal_is_green_and_declining_is_red():
    nominal = [d for _, d in generate_readings(30, scenario="nominal")]
    declining = [d for _, d in generate_readings(30, scenario="declining")]
    assert evaluate(nominal).overall == "green"
    assert evaluate(declining).overall == "red"


def test_donki_offline_fallback_summarizes_cleanly():
    from datetime import date
    from src.nasa_loader import fetch_flares, summarize_by_day
    start, end = date(2026, 1, 1), date(2026, 1, 31)
    records, mode = fetch_flares(start, end, api_key="DEMO_KEY", timeout=0.001)
    assert mode in ("live", "offline-fallback")
    by_day = summarize_by_day(records, start, end)
    assert len(by_day) == 31
    assert all(0 <= v.day.toordinal() for v in by_day.values())


def test_radiation_scales_with_real_flare_risk():
    from datetime import date
    from src.nasa_loader import FlareDaySummary
    quiet = [FlareDaySummary(date(2026, 1, 1), 0, "-", 1.0) for _ in range(5)]
    stormy = [FlareDaySummary(date(2026, 1, 1), 1, "X1.0", 4.0) for _ in range(5)]
    quiet_doses = [d["radiation_msv_day"] for _, d in generate_readings(5, radiation_risk=quiet)]
    stormy_doses = [d["radiation_msv_day"] for _, d in generate_readings(5, radiation_risk=stormy)]
    assert sum(stormy_doses) > sum(quiet_doses)
