"""P2 : règles de sécurité et moteur qui les applique.

Une règle est une fonction qui reçoit un événement et la configuration,
puis renvoie une alerte (dictionnaire) ou None.
"""

from collections.abc import Callable, Iterable, Iterator


def make_alert(record: dict, alert_type: str, message: str) -> dict:
    """Construire une alerte au format convenu avec P3."""
    return {
        "type": alert_type,
        "timestamp": record["timestamp"].isoformat(),
        "ip": record["ip"],
        "user_id": record["user_id"],
        "message": message,
    }


def rule_blacklist(record: dict, **config: object) -> dict | None:
    """Alerter si l'IP figure dans config["blacklist"].

    Sans blacklist, KeyError signale l'erreur de configuration.
    """
    blacklist = config["blacklist"]
    if record["ip"] in blacklist:
        return make_alert(
            record, "blacklist", "IP présente dans la blacklist"
        )
    return None


def rule_critical(record: dict, **config: object) -> dict | None:
    """Alerter si l'événement est de niveau CRITICAL (règle facultative)."""
    if record["level"] == "CRITICAL":
        return make_alert(record, "critical", "Événement de niveau CRITICAL")
    return None


def apply_security_rules(
    *rules: Callable[..., dict | None],
    records: Iterable[dict],
    **config: object,
) -> Iterator[dict]:
    """Appliquer les règles à chaque événement et le renvoyer avec ses alertes.

    *rules regroupe les fonctions reçues, **config les paramètres nommés.
    records, placé après *rules, doit être donné par son nom. Tous les
    événements ressortent, même sans alerte.
    """
    for record in records:
        # Alertes de cet événement seulement : rien n'est accumulé
        alerts = list(record.get("alerts", []))
        for rule in rules:
            alert = rule(record, **config)
            if alert is not None:
                alerts.append(alert)

        checked_record = record.copy()
        checked_record["alerts"] = alerts
        yield checked_record
