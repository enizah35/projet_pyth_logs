from collections import defaultdict
from collections.abc import Iterable

# Niveaux dont l'IP est considérée comme erreur 
ERROR_LEVELS = frozenset({"ERROR", "CRITICAL"})


def analyze(
    records: Iterable[dict], blacklist: frozenset[str], threshold: int
) -> dict:
    """Compter les événements et relever les IP actives et en erreur.

    records : flux d'événements normalisés et enrichis par P2.
    blacklist et threshold servent aux étapes suivantes (ensembles,
    détection de force brute).
    """
    total = 0
    by_level: defaultdict[str, int] = defaultdict(int)
    by_user: defaultdict[str, int] = defaultdict(int)
    active_ips: set[str] = set()
    error_ips: set[str] = set()

    # Un seul passage 
    for record in records:
        total += 1
        by_level[record["level"]] += 1
        by_user[record["user_id"]] += 1
        active_ips.add(record["ip"])
        if record["level"] in ERROR_LEVELS:
            error_ips.add(record["ip"])

    return {
        "total": total,
        "by_level": dict(by_level),
        "by_user": dict(by_user),
        "active_ips": active_ips,
        "error_ips": error_ips,
    }