from collections import defaultdict
from collections.abc import Iterable
 
from logengine.detection import BruteForceDetector, is_login_attempt
 
ERROR_LEVELS = frozenset({"ERROR", "CRITICAL"})
ALERT_TYPES = ("blacklist", "brute_force")
MAX_ALERT_SAMPLES = 20
 
 
def analyze(
    records: Iterable[dict], blacklist: frozenset[str], threshold: int
) -> dict:
    """Produire le bilan du flux : compteurs, IP, alertes.
 
    records : flux d'événements normalisés et enrichis par P2.
    blacklist : IP interdites, comparées aux IP actives.
    threshold : nombre d'échecs consécutifs qui déclenche la force brute.
    """
    detector = BruteForceDetector(threshold)
    total = 0
    by_level: defaultdict[str, int] = defaultdict(int)
    by_user: defaultdict[str, int] = defaultdict(int)
    alerts_by_type: defaultdict[str, int] = defaultdict(int)
    for alert_type in ALERT_TYPES:
        alerts_by_type[alert_type] = 0
    alert_samples: list[dict] = []
    active_ips: set[str] = set()
    error_ips: set[str] = set()
 
    def record_alert(alert: dict) -> None:
        """Compter chaque alerte, mais n'en garder que quelques exemples."""
        alerts_by_type[alert["type"]] += 1
        if len(alert_samples) < MAX_ALERT_SAMPLES:
            alert_samples.append(alert)
 
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
    """Croiser les IP vues dans le flux avec la blacklist immuable."""
    return {
        "union": active_ips | blacklist,
        "intersection": active_ips & blacklist,
        "active_only": active_ips - blacklist,
        "blacklist_only": blacklist - active_ips,
        "symmetric_difference": active_ips ^ blacklist,
    }
 