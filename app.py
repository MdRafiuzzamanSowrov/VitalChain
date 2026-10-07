"""VitalChain: offline-first astronaut health dashboard with a tamper-evident log.

Run:  streamlit run app.py
All data shown is SIMULATED. Not a medical device, not a diagnosis.
"""
from datetime import date as _date
from pathlib import Path

import pandas as pd
import streamlit as st

from src import demo_attacks
from src.chain import HealthLog, load_or_create_key
from src.nasa_loader import mission_risk_series
from src.simulator import generate_readings
from src.status import RULES, evaluate

st.set_page_config(page_title="VitalChain", page_icon="🛰️", layout="wide")

DATA_DIR = Path("data")
LOG_PATH = DATA_DIR / "log.jsonl"
KEY = load_or_create_key(DATA_DIR / "device.key")
EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def load_log() -> HealthLog:
    if LOG_PATH.exists():
        return HealthLog.load(LOG_PATH, KEY)
    return HealthLog(KEY)


if "log" not in st.session_state:
    st.session_state.log = load_log()
log: HealthLog = st.session_state.log

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("Simulated mission data")
    st.caption("All readings are synthetic and labelled as simulated.")
    days = st.slider("Mission days", 7, 90, 30)
    scenario = st.selectbox("Scenario", ["nominal", "declining"])
    use_nasa = st.checkbox("Drive radiation from real NASA DONKI solar data", value=True)
    if st.button("Generate new log", use_container_width=True):
        risk_series, mode = (mission_risk_series(days, _date(2026, 1, 1))
                             if use_nasa else (None, "off"))
        st.session_state.donki_mode = mode
        new = HealthLog(KEY)
        for ts, data in generate_readings(days, scenario=scenario, radiation_risk=risk_series):
            new.append(data, ts)
        new.save(LOG_PATH)
        st.session_state.log = new
        st.rerun()
    if "donki_mode" in st.session_state:
        mode = st.session_state.donki_mode
        if mode == "live":
            st.caption("🛰️ Radiation signal: **live NASA DONKI** solar flare data.")
        elif mode == "offline-fallback":
            st.caption("🛰️ Radiation signal: NASA DONKI unreachable, using bundled "
                       "offline example data (data/donki_flr_sample.json).")
        else:
            st.caption("Radiation signal: purely simulated (NASA data off).")

    st.divider()
    st.header("Red team: tamper with the log")
    if len(log.records) >= 3:
        attack = st.selectbox("Attack", [
            "Edit a past reading",
            "Delete a reading",
            "Forge chain (recompute hashes without the key)",
        ])
        idx = st.slider("Record index", 0, len(log.records) - 2, min(2, len(log.records) - 2))
        if st.button("Launch attack", type="primary", use_container_width=True):
            if attack.startswith("Edit"):
                demo_attacks.edit(log, idx, "sleep_hours", 9.9)
            elif attack.startswith("Delete"):
                demo_attacks.delete(log, idx)
            else:
                demo_attacks.forge(log, idx, "sleep_hours", 9.9)
            log.save(LOG_PATH)
            st.rerun()
        st.caption("To restore a clean log, press Generate new log.")
    else:
        st.caption("Generate a log first.")

# ---------------- main ----------------
st.title("🛰️ VitalChain")
st.caption("Offline-first health self-monitoring for long space missions, with a "
           "tamper-evident log. Simulated data only. Shows indicators, not diagnoses.")

if not log.records:
    st.info("No log yet. Use **Generate new log** in the sidebar.")
    st.stop()

# Integrity is re-checked on every render.
result = log.verify()
if result.ok:
    st.success(f"✅ Log integrity verified: all {result.checked} records chain correctly.")
else:
    st.error(f"🚨 Log integrity FAILED at record {result.bad_index}: {result.reason}. "
             "Readings from this point on cannot be trusted.")

assessment = evaluate([r.data for r in log.records])
st.subheader(f"Current status: {EMOJI[assessment.overall]} {assessment.overall.upper()}")
st.caption(f"Based on the average of the last {assessment.window} readings.")

# Safe check for st.columns to prevent StreamlitInvalidColumnSpecError when indicators is empty
if assessment.indicators:
    cols = st.columns(len(assessment.indicators))
    for col, ind in zip(cols, assessment.indicators):
        with col:
            st.metric(ind.label, f"{ind.value} {ind.unit}")
            st.write(f"{EMOJI[ind.level]} {ind.level}")
else:
    st.info("No indicators found to display.")

for ind in assessment.indicators:
    if ind.advice:
        st.warning(f"**{ind.label}:** {ind.advice}")

# Safe DataFrame index creation using enumerate()
df = pd.DataFrame([
    {"day": idx, **r.data} for idx, r in enumerate(log.records)
]).set_index("day")

tabs = st.tabs([RULES[k]["label"] for k in RULES])
for tab, key in zip(tabs, RULES):
    with tab:
        st.line_chart(df[key])

with st.expander("Inspect the hash chain"):
    st.dataframe(pd.DataFrame([{
        "record": idx,
        "timestamp": r.timestamp,
        "prev_hash": r.prev_hash[:12] + "…",
        "hash": r.hash[:12] + "…",
    } for idx, r in enumerate(log.records)]), use_container_width=True, hide_index=True)
    st.caption("Limitation: deleting only the very last record is not detectable from the chain "
               "alone. Anchor the latest hash elsewhere (crew display or Earth sync) to catch it.")
