"""P2 : démonstration du pipeline et des règles sur trois événements.

Lancement : python main.py --demo-p2
"""

from collections.abc import Callable
from datetime import datetime
import os

from logengine.audit import export_audit
from logengine.pipeline import normalize_records
from logengine.rules import (
    apply_security_rules,
    rule_blacklist,
    rule_critical,
)


def sample_records() -> tuple[dict, ...]:
    """Renvoyer trois événements au format du parseur de P1."""
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


def run_scenario(title: str, *rules: Callable[..., dict | None]) -> None:
    """Traiter les événements avec les règles reçues et afficher le bilan."""
    blacklist = frozenset({"192.168.1.66", "192.168.1.99"})
    records = normalize_records(sample_records())
    # *rules transmet les fonctions reçues une par une
    checked = apply_security_rules(
        *rules, records=records, blacklist=blacklist
    )

    print(f"--- {title} ---")
    total = 0
    alert_count = 0
    for record in checked:
        total += 1
        print(record["message"])
        for alert in record["alerts"]:
            alert_count += 1
            print(f"  ALERTE {alert['type']}: {alert['message']}")
    print(f"Bilan : {total} événements, {alert_count} alerte(s).")
    print()


def main() -> None:
    """Lancer deux scénarios de règles, puis exporter l'audit."""
    run_scenario("Règle blacklist seule", rule_blacklist)
    # Une règle de plus, sans modifier le moteur
    run_scenario("Règles blacklist et critical", rule_blacklist, rule_critical)

    # Dossier parent de examples/
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    audit_path = os.path.join(project_dir, "output", "p2", "audit.json")
    export_audit(audit_path, globals(), locals())
    print(f"Audit : {audit_path}")
    print("La détection de force brute est faite par P3.")


if __name__ == "__main__":
    main()
