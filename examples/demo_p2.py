"""Démonstration P2 sur dictionnaires manuels : python -m examples.demo_p2."""

from datetime import datetime
from pathlib import Path

from logengine.audit import export_audit
from logengine.pipeline import normalize_records
from logengine.rules import apply_security_rules, rule_blacklist


def sample_records() -> tuple[dict, ...]:
    """Petit exemple P2 ; le lecteur et le parseur de fichiers restent à P1."""
    return (
        {
            "timestamp": datetime(2026, 11, 5, 10, 0, 1),
            "level": " warning ",
            "ip": "192.168.1.20",
            "user_id": " bob ",
            "connection": ("192.168.1.20", 443, " https "),
            "payload": {"event": "login", "status": "failure"},
        },
        {
            "timestamp": datetime(2026, 11, 5, 10, 0, 5),
            "level": "CRITICAL",
            "ip": "192.168.1.66",
            "user_id": "carol",
            "connection": ("192.168.1.66", 443, "HTTPS"),
            "payload": {"event": "request", "status": "denied"},
        },
        {
            "timestamp": datetime(2026, 11, 5, 10, 0, 8),
            "level": "INFO",
            "ip": "192.168.1.30",
            "user_id": "service",
            "connection": ("192.168.1.30", 443, "HTTPS"),
            "payload": " Health check OK ",
        },
    )


def main() -> None:
    """Afficher les trois événements, l'alerte et le chemin de l'audit."""
    blacklist = frozenset({"192.168.1.66", "192.168.1.99"})
    records = normalize_records(sample_records())
    checked = apply_security_rules(
        rule_blacklist, records=records, blacklist=blacklist
    )
    total = 0
    alert_count = 0
    for record in checked:
        total += 1
        print(record["message"])
        for alert in record["alerts"]:
            alert_count += 1
            print(f"  ALERTE {alert['type']}: {alert['message']}")

    audit_path = Path(__file__).resolve().parents[1] / "output/p2/audit.json"
    export_audit(audit_path, globals(), locals())
    print(f"\nBilan P2 : {total} événements, {alert_count} alerte blacklist.")
    print(f"Audit : {audit_path}")
    print("La détection de force brute sera fournie par P3.")


if __name__ == "__main__":
    main()
