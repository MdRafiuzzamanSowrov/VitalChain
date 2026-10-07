"""Tamper-evident health log.

Every record stores the hash of the previous record, so editing or removing an
old record breaks the chain. Hashes are HMAC-SHA256 keyed with a per-device
secret, so an attacker who can edit the log file but does not hold the key
cannot simply recompute the whole chain to hide their edit.

Known limitation (documented on purpose): deleting the *last* record leaves a
valid chain. To catch that, anchor the latest hash (see HealthLog.head()) in
a second place, e.g. show it to the crew or sync it to Earth when a link exists.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

GENESIS_HASH = "0" * 64


def _canonical(obj) -> bytes:
    """Stable byte encoding so the same data always hashes the same way."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def compute_hash(index: int, timestamp: str, data: dict, prev_hash: str,
                 key: Optional[bytes]) -> str:
    payload = _canonical(
        {"index": index, "timestamp": timestamp, "data": data, "prev_hash": prev_hash}
    )
    if key:
        return hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload).hexdigest()


def load_or_create_key(path: Path) -> bytes:
    """Device secret. Generated once, kept local, never committed to git."""
    path = Path(path)
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = os.urandom(32)
    path.write_bytes(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


@dataclass
class Record:
    index: int
    timestamp: str
    data: dict
    prev_hash: str
    hash: str


@dataclass
class VerifyResult:
    ok: bool
    bad_index: Optional[int] = None
    reason: str = ""
    checked: int = 0


class HealthLog:
    def __init__(self, key: Optional[bytes] = None):
        self.key = key
        self.records: list[Record] = []

    def head(self) -> str:
        return self.records[-1].hash if self.records else GENESIS_HASH

    def append(self, data: dict, timestamp: Optional[str] = None) -> Record:
        index = len(self.records)
        ts = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
        prev = self.head()
        rec = Record(index, ts, dict(data), prev,
                     compute_hash(index, ts, data, prev, self.key))
        self.records.append(rec)
        return rec

    def verify(self) -> VerifyResult:
        prev = GENESIS_HASH
        for i, rec in enumerate(self.records):
            if rec.index != i:
                return VerifyResult(False, i, "record missing or out of order", i)
            if rec.prev_hash != prev:
                return VerifyResult(False, i, "link to the previous record is broken", i)
            expected = compute_hash(rec.index, rec.timestamp, rec.data,
                                    rec.prev_hash, self.key)
            if not hmac.compare_digest(expected, rec.hash):
                return VerifyResult(False, i, "record content does not match its hash", i)
            prev = rec.hash
        return VerifyResult(True, None, "", len(self.records))

    # --- persistence (JSON Lines: one record per line) ---
    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(asdict(rec)) + "\n")

    @classmethod
    def load(cls, path: Path, key: Optional[bytes] = None) -> "HealthLog":
        log = cls(key)
        with Path(path).open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    log.records.append(Record(**json.loads(line)))
        return log
