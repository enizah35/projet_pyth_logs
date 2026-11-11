"""P3 : statistiques, ensembles d'IP et comptage des alertes.

Le flux est parcouru une seule fois ; seuls des compteurs et quelques
exemples d'alertes sont conservés.
"""

from collections import defaultdict
from collections.abc import Iterable

from logengine.detection import BruteForceDetector, is_login_attempt

ERROR_LEVELS = frozenset({"ERROR", "CRITICAL"})
ALERT_TYPES = ("blacklist", "brute_force")
MAX_ALERT_SAMPLES = 20


def analyze(
    records: Iterable[dict], blacklist: frozenset[str], threshold: int
) -> dict:
    """Produire le bilan du flux : compteurs, IP et alertes.

    threshold est le nombre d'échecs consécutifs qui déclenche une alerte.
    """
    detector = BruteForceDetector(threshold)
    total = 0
    by_level: defaultdict[str, int] = defaultdict(int)
    by_user: defaultdict[str, int] = defaultdict(int)
    alerts_by_type: defaultdict[str, int] = defaultdict(int)
    # Afficher aussi les types sans alerte
    for alert_type in ALERT_TYPES:
        alerts_by_type[alert_type] = 0
    alert_samples: list[dict] = []
    active_ips: set[str] = set()
    error_ips: set[str] = set()

    def record_alert(alert: dict) -> None:
        """Compter l'alerte et la garder si l'échantillon n'est pas plein."""
        alerts_by_type[alert["type"]] += 1
        if len(alert_samples) < MAX_ALERT_SAMPLES:
            alert_samples.append(alert)

    # while + next() : StopIteration marque la fin du flux
    events = iter(records)
    while True:
        try:
            record = next(events)
        except StopIteration:
            break

        total += 1
        by_level[record["level"]] += 1
        by_user[record["user_id"]] += 1
        active_ips.add(record["ip"])
        if record["level"] in ERROR_LEVELS:
            error_ips.add(record["ip"])

        for alert in record.get("alerts", []):
            record_alert(alert)

        # Seules les connexions intéressent le détecteur
        if not is_login_attempt(record):
            continue

        alert = detector.process(record)
        if alert is not None:
            record_alert(alert)

    return {
        "total": total,
        "by_level": dict(by_level),
        "by_user": dict(by_user),
        "active_ips": active_ips,
        "error_ips": error_ips,
        "ip_sets": compare_with_blacklist(active_ips, blacklist),
        "alerts_by_type": dict(alerts_by_type),
        "alert_samples": alert_samples,
    }


def compare_with_blacklist(
    active_ips: set[str], blacklist: frozenset[str]
) -> dict[str, set[str]]:
    """Comparer les IP actives à la blacklist (|, &, -, ^)."""
    return {
        "union": active_ips | blacklist,
        "intersection": active_ips & blacklist,
        "active_only": active_ips - blacklist,
        "blacklist_only": blacklist - active_ips,
        "symmetric_difference": active_ips ^ blacklist,
    }

