"""P2 : fonctions de sécurité et moteur de règles extensible."""

from collections.abc import Callable, Iterable, Iterator


def _make_alert(record: dict, alert_type: str, message: str) -> dict:
    """Construire une alerte conforme au contrat partagé avec P1 et P3."""
    return {
        "type": alert_type,
        "timestamp": record["timestamp"].isoformat(),
        "ip": record["ip"],
        "user_id": record["user_id"],
        "message": message,
    }


def rule_blacklist(record: dict, **config) -> dict | None:
    """Signaler une IP figurant dans la blacklist fournie par P1."""
    blacklist = config["blacklist"]
    if record["ip"] in blacklist:
        return _make_alert(
            record, "blacklist", "IP présente dans la blacklist"
        )
    return None


def rule_critical(record: dict, **config) -> dict | None:
    """Règle facultative, désactivée dans le scénario de référence."""
    if record["level"] == "CRITICAL":
        return _make_alert(record, "critical", "Événement de niveau CRITICAL")
    return None


def apply_security_rules(
    *rules: Callable, records: Iterable[dict], **config
) -> Iterator[dict]:
    """Appliquer les fonctions reçues à chaque événement, sans les accumuler.

    Les fonctions sont passées dans *rules et leur configuration dans **config.
    Tous les événements restent présents, même avec une liste alerts vide.
    Une erreur de règle reste visible pour pouvoir être corrigée.
    """
    for record in records:
        # La liste concerne seulement cet événement, jamais le flux entier.
        alerts = list(record.get("alerts", []))
        for rule in rules:
            # **config transmet les paramètres nommés à chaque règle.
            alert = rule(record, **config)
            if alert is not None:
                alerts.append(alert)
        checked_record = record.copy()
        checked_record["alerts"] = alerts
        yield checked_record
