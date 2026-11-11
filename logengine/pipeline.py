"""P2 : nettoyage et normalisation des événements.

Chaque étape renvoie un itérateur (map, filter) : un événement n'est
calculé que lorsque l'étape suivante le demande.
"""

from collections.abc import Callable, Iterable, Iterator

from .parsing import parse_line

# frozenset : ensemble non modifiable, recherche "in" rapide
LEVELS = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})


def route_value(value: object) -> dict:
    """Reconnaître le format d'une valeur (texte, événement, connexion).

    Renvoie le format ("kind"), la valeur et un résumé lisible.
    """
    match value:
        case str():
            return {"kind": "text", "value": value, "summary": value}

        # Motif de dictionnaire : capture les valeurs, accepte d'autres clés
        case {"event": str() as event, "status": str() as status}:
            return {
                "kind": "event",
                "value": value,
                "summary": f"{event} : {status}",
            }

        case {"level": str() as level, "code": int() as code}:
            return {
                "kind": "event",
                "value": value,
                "summary": f"{level} code {code}",
            }

        case dict():
            return {
                "kind": "event",
                "value": value,
                "summary": "événement structuré",
            }

        # Motif de séquence : la condition écarte les listes
        case (str() as ip, int() as port, str() as protocol) if isinstance(
            value, tuple
        ):
            return {
                "kind": "connection",
                "value": value,
                "summary": f"{protocol} {ip}:{port}",
            }

        case _:
            return {
                "kind": "unknown",
                "value": value,
                "summary": "format non reconnu",
            }


def normalize_record(record: dict) -> dict:
    """Renvoyer une copie nettoyée (" warning " devient "WARNING")."""
    normalized = record.copy()
    normalized["level"] = record["level"].strip().upper()
    normalized["ip"] = record["ip"].strip()
    normalized["user_id"] = record["user_id"].strip()

    # Un tuple ne se modifie pas : on en construit un nouveau
    ip, port, protocol = record["connection"]
    normalized["connection"] = (ip.strip(), port, protocol.strip().upper())

    payload = record["payload"]
    if isinstance(payload, str):
        payload = payload.strip()
    normalized["payload"] = payload

    normalized["payload_description"] = route_value(payload)
    normalized["connection_description"] = route_value(
        normalized["connection"]
    )
    normalized["message"] = (
        f"{normalized['timestamp'].isoformat()} [{normalized['level']}] "
        f"user={normalized['user_id']} ip={normalized['ip']} "
        f"{payload}"
    )
    return normalized


def has_known_level(record: dict) -> bool:
    """Indiquer si le niveau fait partie des quatre niveaux acceptés."""
    if record["level"] in LEVELS:
        return True
    print(f"Événement ignoré : niveau inconnu {record['level']!r}")
    return False


def normalize_records(records: Iterable[dict]) -> Iterator[dict]:
    """Normaliser un flux d'événements puis retirer les niveaux inconnus."""
    normalized = map(normalize_record, records)
    # Filtrer après normalisation : " debug " doit d'abord devenir "DEBUG"
    return filter(has_known_level, normalized)


def build_pipeline(
    lines: Iterable[str],
    parser: Callable[[str], dict | None] = parse_line,
) -> Iterator[dict]:
    """Transformer des lignes de log en événements nettoyés.

    parser est remplaçable pour tester P2 sans le parseur de P1.
    """
    # filter + lambda : écarter les lignes vides
    nonempty_lines = filter(lambda line: line.strip() != "", lines)
    # map reçoit la fonction sans l'appeler : il l'appelle ligne par ligne
    parsed_records = map(parser, nonempty_lines)
    # filter(None, ...) : retirer les None des lignes invalides
    valid_records = filter(None, parsed_records)
    return normalize_records(valid_records)
