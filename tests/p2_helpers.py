"""Outils de test P2 : événement minimal au format du parseur."""

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
