"""Données minimales des tests P2, indépendantes des modules P1 et P3."""

from datetime import datetime


def make_record(**changes) -> dict:
    record = {
        "timestamp": datetime(2026, 11, 5, 10, 0, 1),
        "level": "INFO",
        "ip": "192.168.1.20",
        "user_id": "bob",
        "connection": ("192.168.1.20", 443, "HTTPS"),
        "payload": {"event": "login", "status": "failure"},
    }
    record.update(changes)
    return record
