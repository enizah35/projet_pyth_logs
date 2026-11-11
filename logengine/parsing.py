"""P1 : transformation d'une ligne JSON en dictionnaire typé.

Les valeurs ne sont pas normalisées : c'est le rôle de P2.
"""

import json
import logging
from datetime import datetime

LOGGER = logging.getLogger(__name__)
REQUIRED_FIELDS = (
    "timestamp", "level", "ip", "user_id", "connection", "payload",
)


def parse_line_details(line: str) -> tuple[dict | None, str]:
    """Renvoyer (événement ou None, cause), pour le mode --details.

    Les champs supplémentaires sont conservés.
    """
    if not line.strip():
        return None, "ligne vide ignorée"
    try:
        record = json.loads(line)
    except json.JSONDecodeError as error:
        return None, f"JSON malformé ({error.msg})"
    if not isinstance(record, dict):
        return None, "la racine doit être un objet JSON"
    for field in REQUIRED_FIELDS:
        if field not in record:
            return None, f"champ manquant : {field}"
    for field in ("timestamp", "level", "ip", "user_id"):
        if not isinstance(record[field], str):
            return None, f"{field} doit être une chaîne"
    connection = record["connection"]
    if not (
        isinstance(connection, list)
        and len(connection) == 3
        and isinstance(connection[0], str)
        # bool hérite de int : type() écarte True et False
        and type(connection[1]) is int
        and isinstance(connection[2], str)
    ):
        return None, "connection doit être [str, int, str]"
    payload = record["payload"]
    if not (isinstance(payload, dict) or isinstance(payload, str)):
        return None, "payload doit être un objet ou une chaîne"
    try:
        timestamp = datetime.fromisoformat(record["timestamp"])
    except ValueError:
        return None, "timestamp ISO invalide"
    record["timestamp"] = timestamp
    record["connection"] = tuple(connection)
    return record, "événement valide"


def parse_line(line: str) -> dict | None:
    """Renvoyer l'événement ou None, et signaler les lignes rejetées.

    Une ligne vide est ignorée sans avertissement.
    """
    record, reason = parse_line_details(line)
    if record is None and line.strip():
        LOGGER.warning("Ligne rejetée : %s ; extrait=%r", reason, line[:160])
    return record
