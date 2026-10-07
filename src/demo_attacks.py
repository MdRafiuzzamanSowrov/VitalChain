"""Red-team helpers used by the demo and the tests. These simulate an attacker
(or a faulty sensor) altering the stored log."""
from __future__ import annotations

from .chain import HealthLog, compute_hash


def edit(log: HealthLog, i: int, field: str, value) -> None:
    """Change one stored value, leave the hashes alone."""
    log.records[i].data[field] = value


def delete(log: HealthLog, i: int) -> None:
    """Remove a record from the middle of the log."""
    del log.records[i]


def forge(log: HealthLog, i: int, field: str, value) -> None:
    """Smarter attack: edit a value, then recompute every later hash with plain
    SHA-256 so the chain *looks* consistent. Works against an unkeyed chain,
    fails against the device-keyed HMAC chain."""
    log.records[i].data[field] = value
    prev = log.records[i - 1].hash if i > 0 else log.records[0].prev_hash
    for rec in log.records[i:]:
        rec.prev_hash = prev
        rec.hash = compute_hash(rec.index, rec.timestamp, rec.data, prev, key=None)
        prev = rec.hash
