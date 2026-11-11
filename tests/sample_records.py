"""Outils de test P3 : événements et blacklist de référence."""

from datetime import datetime

BLACKLIST = frozenset({"192.168.1.99", "192.168.1.66"})

RECORDS = [
    # ligne 1
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 0),
        "level": "INFO",
        "ip": "192.168.1.10",
        "user_id": "alice",
        "connection": ("192.168.1.10", 443, "HTTPS"),
        "payload": {"event": "login", "status": "success"},
        "alerts": [],
    },
    # ligne 2 (niveau " warning " normalisé par P2)
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 1),
        "level": "WARNING",
        "ip": "192.168.1.20",
        "user_id": "bob",
        "connection": ("192.168.1.20", 443, "HTTPS"),
        "payload": {"event": "login", "status": "failure"},
        "alerts": [],
    },
    # ligne 3
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 2),
        "level": "INFO",
        "ip": "192.168.1.10",
        "user_id": "alice",
        "connection": ("192.168.1.10", 443, "HTTPS"),
        "payload": {"event": "request", "path": "/home", "status": "success"},
        "alerts": [],
    },
    # ligne 4
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 3),
        "level": "WARNING",
        "ip": "192.168.1.20",
        "user_id": "bob",
        "connection": ("192.168.1.20", 443, "HTTPS"),
        "payload": {"event": "login", "status": "failure"},
        "alerts": [],
    },
    # ligne 5 (3e échec de bob : seuil atteint)
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 4),
        "level": "ERROR",
        "ip": "192.168.1.20",
        "user_id": "bob",
        "connection": ("192.168.1.20", 443, "HTTPS"),
        "payload": {"event": "login", "status": "failure"},
        "alerts": [],
    },
    # ligne 6 (IP blacklistée : alerte ajoutée par la règle de P2)
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 5),
        "level": "CRITICAL",
        "ip": "192.168.1.66",
        "user_id": "carol",
        "connection": ("192.168.1.66", 443, "HTTPS"),
        "payload": {"event": "request", "path": "/admin", "status": "denied"},
        "alerts": [
            {
                "type": "blacklist",
                "timestamp": "2026-11-05T10:00:05",
                "ip": "192.168.1.66",
                "user_id": "carol",
                "message": "IP présente dans la blacklist",
            }
        ],
    },
    # ligne 7 (réussite de bob : remise à zéro)
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 6),
        "level": "INFO",
        "ip": "192.168.1.20",
        "user_id": "bob",
        "connection": ("192.168.1.20", 443, "HTTPS"),
        "payload": {"event": "login", "status": "success"},
        "alerts": [],
    },
    # ligne 8 (nouvel échec isolé de bob : pas d'alerte)
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 7),
        "level": "WARNING",
        "ip": "192.168.1.20",
        "user_id": "bob",
        "connection": ("192.168.1.20", 443, "HTTPS"),
        "payload": {"event": "login", "status": "failure"},
        "alerts": [],
    },
    # ligne 9 (payload en chaîne brute)
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 8),
        "level": "INFO",
        "ip": "192.168.1.30",
        "user_id": "service",
        "connection": ("192.168.1.30", 443, "HTTPS"),
        "payload": "Health check OK",
        "alerts": [],
    },
    # ligne 10 (erreur de requête : ce n'est pas un échec de connexion)
    {
        "timestamp": datetime(2026, 11, 5, 10, 0, 9),
        "level": "ERROR",
        "ip": "192.168.1.10",
        "user_id": "alice",
        "connection": ("192.168.1.10", 443, "HTTPS"),
        "payload": {
            "event": "request", "path": "/report", "status": "failure",
        },
        "alerts": [],
    },
]
