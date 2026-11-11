"""P2 : règles de sécurité et moteur qui les applique.

Une règle est une simple fonction : elle reçoit un événement et la
configuration, puis renvoie une alerte (un dictionnaire) ou None.
Le moteur reçoit ces fonctions en arguments, ce qui permet d'ajouter une
règle sans toucher au moteur.

Callable[..., dict | None] désigne une fonction, quels que soient ses
arguments, qui renvoie un dictionnaire ou None : c'est le type d'une règle.
"""

from collections.abc import Callable, Iterable, Iterator


def make_alert(record: dict, alert_type: str, message: str) -> dict:
    """Construire une alerte au format convenu avec P1 et P3."""
    return {
        "type": alert_type,
        # La date est convertie en texte pour pouvoir être affichée en JSON.
        "timestamp": record["timestamp"].isoformat(),
        "ip": record["ip"],
        "user_id": record["user_id"],
        "message": message,
    }


def rule_blacklist(record: dict, **config: object) -> dict | None:
    """Alerte si l'IP de l'événement figure dans la blacklist.

    La blacklist arrive par la configuration : config["blacklist"].
    Si elle est absente, Python lève KeyError : c'est une erreur de
    configuration qu'il vaut mieux voir tout de suite.
    """
    blacklist = config["blacklist"]
    if record["ip"] in blacklist:
        return make_alert(
            record, "blacklist", "IP présente dans la blacklist"
        )
    return None


def rule_critical(record: dict, **config: object) -> dict | None:
    """Alerte si l'événement est de niveau CRITICAL.

    Deuxième règle, facultative : elle montre que le moteur accepte
    plusieurs règles. Elle n'utilise pas la configuration, mais garde
    **config pour avoir la même signature que les autres règles.
    """
    if record["level"] == "CRITICAL":
        return make_alert(record, "critical", "Événement de niveau CRITICAL")
    return None


def apply_security_rules(
    *rules: Callable[..., dict | None],
    records: Iterable[dict],
    **config: object,
) -> Iterator[dict]:
    """Appliquer chaque règle à chaque événement, un événement à la fois.

    *rules   : les fonctions de règles, regroupées par Python dans un tuple.
               Il peut y en avoir zéro, une ou plusieurs.
    records  : le flux d'événements. Placé après *rules, il doit être
               donné par son nom : records=...
    **config : les paramètres nommés restants (blacklist=...), regroupés
               dans un dictionnaire et transmis tels quels aux règles.

    Exemple :
        apply_security_rules(rule_blacklist, rule_critical,
                             records=flux, blacklist=ips)

    Tous les événements ressortent, même sans alerte : P3 en a besoin
    pour ses statistiques. Chacun reçoit un champ "alerts" (une liste).
    """
    for record in records:
        # Cette liste ne concerne que l'événement en cours. On ne garde
        # jamais les alertes de tout le fichier en mémoire.
        alerts = list(record.get("alerts", []))

        for rule in rules:
            # rule est une fonction rangée dans une variable : on l'appelle
            # normalement. **config redonne blacklist=... à la règle.
            alert = rule(record, **config)
            if alert is not None:
                alerts.append(alert)

        # Copie pour ne pas modifier l'événement reçu.
        checked_record = record.copy()
        checked_record["alerts"] = alerts
        # yield renvoie cet événement et met la fonction en pause jusqu'à
        # ce que l'étape suivante en demande un autre.
        yield checked_record
