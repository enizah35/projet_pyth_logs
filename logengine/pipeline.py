"""P2 : nettoyage et transformation progressive des événements.

Le parseur P1 vérifie JSON, les types et les champs obligatoires.
Ce module reçoit des dictionnaires conformes au contrat de l'équipe.
"""

from collections.abc import Callable, Iterable, Iterator
import logging


LEVELS = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})
LOGGER = logging.getLogger(__name__)


def route_value(value: object) -> dict:
    """Décrire le format d'un payload ou d'une connexion avec match-case."""
    match value:
        case str() as text:
            return {"kind": "text", "value": text}
        case dict() as event:
            return {"kind": "event", "value": event}
        case (str(), int(), str()) if isinstance(value, tuple):
            return {"kind": "connection", "value": value}
        case _:
            return {"kind": "unknown", "value": value}


def normalize_record(record: dict) -> dict:
    """Normaliser un événement sans modifier le dictionnaire reçu."""
    normalized = record.copy()
    normalized["level"] = record["level"].strip().upper()
    normalized["ip"] = record["ip"].strip()
    normalized["user_id"] = record["user_id"].strip()

    ip, port, protocol = record["connection"]
    normalized["connection"] = (ip.strip(), port, protocol.strip().upper())

    payload = record["payload"]
    if isinstance(payload, str):
        normalized["payload"] = payload.strip()
    else:
        normalized["payload"] = payload
    normalized["payload_description"] = route_value(normalized["payload"])
    normalized["connection_description"] = route_value(
        normalized["connection"]
    )
    normalized["message"] = (
        f"{normalized['timestamp'].isoformat()} [{normalized['level']}] "
        f"user={normalized['user_id']} ip={normalized['ip']} "
        f"{normalized['payload']}"
    )
    return normalized


def _has_known_level(record: dict) -> bool:
    """Rejeter un niveau inconnu après sa normalisation."""
    if record["level"] in LEVELS:
        return True
    LOGGER.warning("Événement ignoré : niveau inconnu %r", record["level"])
    return False


def normalize_records(records: Iterable[dict]) -> Iterator[dict]:
    """Nettoyer un flux de dictionnaires, sans le charger dans une liste."""
    normalized = map(normalize_record, records)
    return filter(_has_known_level, normalized)


def build_pipeline(
    lines: Iterable[str], *, parser: Callable | None = None
) -> Iterator[dict]:
    """Relier les lignes de P1 au nettoyage de P2, à la demande.

    L'appel public habituel est build_pipeline(lines). Le paramètre facultatif
    parser permet de tester P2 indépendamment avant la livraison du parseur P1.
    """
    if parser is None:
        # Import différé pour utiliser les autres fonctions P2 sans P1.
        from .parsing import parse_line

        parser = parse_line

    # filter conserve uniquement les lignes pour lesquelles le test est vrai.
    nonempty_lines = filter(lambda line: bool(line.strip()), lines)
    # On passe la fonction parser sans parenthèses : map l'appelle par ligne.
    parsed_records = map(parser, nonempty_lines)
    # P1 renvoie None pour une ligne invalide ; filter(None, ...) l'élimine.
    valid_records = filter(None, parsed_records)
    # yield from transmet les événements un par un à l'étape suivante.
    yield from normalize_records(valid_records)
