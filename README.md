# VitalChain (working title)

**An offline-first health dashboard for astronauts, with a tamper-evident health log.**

NASA International Space Apps Challenge 2026 · Bangladesh · Dhaka
Challenge: **Create Health Monitoring Software for Astronauts on Space Missions**
Team: solo, [YOUR NAME]

> Status: prescreening entry (concept + early prototype). The full challenge statement is published on 28 October 2026, and this project will be aligned to it then.

---

## 1. The problem

On long missions to the Moon and Mars, astronauts face radiation, isolation, altered gravity and a closed environment. These can bring immune changes, bone loss, cardiovascular events and behavioral health problems. With communication delays, astronauts carry much of the responsibility for spotting these changes in themselves.

## 2. Our idea

VitalChain gathers health indicators and lets an astronaut evaluate and act on their own health status, even with no connection to Earth.

1. **Self-monitoring dashboard.** Sleep, activity, heart rate, a quick mood/stress check-in and an estimated radiation exposure, shown as a simple green / yellow / red status with a plain-language "what to do next".
2. **Tamper-evident health log.** Every reading is chained to the previous one with a cryptographic hash. If a record is edited, deleted or a sensor value is spoofed, the chain breaks and the dashboard warns the astronaut.
3. **Offline-first.** Data is processed and stored on the device. Nothing needs the network.

Because the astronaut is the one making decisions, they need to be able to trust the data in front of them. That is why integrity is built in.

> VitalChain shows indicators and trends. It does not diagnose medical conditions.

## 3. Architecture

```
[Data source: NASA data / simulated feed]
            |
     [Ingest + validate]
            |
   [Hash-chained log] ---> [Tamper check]
            |                    |
     [Trend + status]      [Integrity alert]
            \                   /
             [Astronaut dashboard]
```

(Replace with a proper diagram image in /docs before submitting.)

## 4. Data

| Data | Source | Status |
|---|---|---|
| Solar flare events (real, live) | **NASA DONKI API** — `api.nasa.gov/DONKI/FLR` | **Integrated** — drives the radiation indicator |
| Vitals (sleep, HR, activity, stress) | **Synthetic / simulated** | Used for the demo, clearly labelled as simulated |
| Health-related space research data | NASA Open Science Data Repository (OSDR) | Candidate, to confirm against the 28 Oct challenge statement |

Real, named-crew medical data is not public, so vitals are simulated and this is stated openly in the dashboard, the demo and the video. What is **not** simulated: the radiation indicator is scaled by real solar flare activity pulled live from NASA's DONKI space-weather feed (`src/nasa_loader.py`). A quiet sun gives a baseline dose; an actual X-class flare day multiplies it up, the same way it would for a real crew. If the live API is unreachable (e.g. no internet in the judging room), the app falls back to a small bundled example (`data/donki_flr_sample.json`) and says so on screen — it never silently pretends offline data is live.

Get a free key at [api.nasa.gov](https://api.nasa.gov) (1,000 req/hr) and set `NASA_API_KEY` before running for higher limits than the shared `DEMO_KEY`.

## 5. Tamper demo

1. Run the simulator to generate readings.
2. Verify the log: status shows **intact**.
3. In the sidebar, launch an attack: edit a reading, delete one, or forge the chain by recomputing hashes.
4. The dashboard flags the log as **tampered** and names the first broken record.

Hashes are HMAC-SHA256 with a per-device key, so even the forge attack fails. The tests include a case showing that a plain unkeyed hash chain can be rewritten, which is why the key matters. Known limitation: deleting only the last record is not caught by the chain alone.

## 6. Use of AI

[List every AI tool you use, what for, and your prompts/reasoning. Fill this in as you go.]

## 7. Tools and technologies

[e.g. Python, Streamlit or React, SQLite, hashlib. Credit every library.]

## 8. Run it

```bash
git clone [REPO URL]
cd [REPO NAME]
pip install -r requirements.txt
streamlit run app.py      # dashboard + tamper demo
python -m pytest          # tests
```

Layout: `app.py` (dashboard), `src/chain.py` (hash-chained log), `src/simulator.py` (synthetic vitals),
`src/status.py` (traffic-light rules), `src/demo_attacks.py` (red-team helpers), `tests/`.

## 9. Roadmap

- Full alignment with the 2026 challenge statement and its linked datasets
- Encryption at rest for the local store
- Role-based sharing with a ground team when a link is available

## 10. References

[Every source, dataset, paper, library and asset used.]

## License

MIT (event code stays open source).
