"""P2 : nettoyage et transformation des événements, un par un.

Le parseur de P1 transforme chaque ligne en dictionnaire (ou None si la
ligne est invalide). Ce module reçoit ces dictionnaires, les nettoie et
élimine ceux qui ne sont pas exploitables.

Rien n'est stocké dans une liste : map() et filter() ne calculent un
élément que lorsque l'étape suivante le demande.

Annotations utilisées (elles documentent le code, sans rien vérifier
pendant l'exécution) :
- Iterable[str] : un objet parcourable avec for, ici des lignes de texte ;
- Iterator[dict] : un objet qui fournit ses dictionnaires un par un ;
- Callable[[str], dict | None] : une fonction qui reçoit une chaîne et
  renvoie un dictionnaire ou None, comme le parseur de P1.
"""

from collections.abc import Callable, Iterable, Iterator

from .parsing import parse_line

# Les quatre niveaux acceptés. Un frozenset ne peut pas être modifié et le
# test "x in LEVELS" est rapide.
LEVELS = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})


def route_value(value: object) -> dict:
    """Reconnaître le format d'une valeur avec match-case.

    Trois formats sont attendus dans un log :
    - une chaîne brute, par exemple "Service unavailable" ;
    - un dictionnaire, par exemple {"event": "login", "status": "failure"}
      ou {"level": "ERROR", "code": 503} ;
    - un tuple de connexion (ip, port, protocole).
    Tout le reste est classé "unknown".

    Le résultat contient le format ("kind"), la valeur d'origine et un
    résumé lisible construit à partir des éléments extraits par le motif.
    """
    match value:
        case str():
            return {"kind": "text", "value": value, "summary": value}

        # Motif de dictionnaire : il vérifie que les clés existent et
        # range leurs valeurs dans les variables event et status.
        # Les autres clés du dictionnaire (comme "path") sont acceptées.
        case {"event": str() as event, "status": str() as status}:
            return {
                "kind": "event",
                "value": value,
                "summary": f"{event} : {status}",
            }

        # Même principe pour un événement d'erreur avec un code numérique.
        case {"level": str() as level, "code": int() as code}:
            return {
                "kind": "event",
                "value": value,
                "summary": f"{level} code {code}",
            }

        # Tout autre dictionnaire reste un événement structuré.
        case dict():
            return {
                "kind": "event",
                "value": value,
                "summary": "événement structuré",
            }

        # Motif de séquence : il déballe les trois éléments et vérifie
        # leurs types. Il accepterait aussi une liste de trois éléments ;
        # la condition après "if" impose un vrai tuple.
        case (str() as ip, int() as port, str() as protocol) if isinstance(
            value, tuple
        ):
            return {
                "kind": "connection",
                "value": value,
                "summary": f"{protocol} {ip}:{port}",
            }

        case _:
            # "_" attrape tous les cas restants, comme un else.
            return {
                "kind": "unknown",
                "value": value,
                "summary": "format non reconnu",
            }


def normalize_record(record: dict) -> dict:
    """Renvoyer une copie nettoyée de l'événement.

    Exemple : " warning " devient "WARNING" et " https " devient "HTTPS".
    Le dictionnaire reçu n'est pas modifié.
    """
    # On travaille sur une copie pour ne pas changer l'événement d'origine.
    normalized = record.copy()

    # strip() retire les espaces autour, upper() met en majuscules.
    normalized["level"] = record["level"].strip().upper()
    normalized["ip"] = record["ip"].strip()
    normalized["user_id"] = record["user_id"].strip()

    # Un tuple ne se modifie pas : on le déballe puis on en construit un autre.
    ip, port, protocol = record["connection"]
    normalized["connection"] = (ip.strip(), port, protocol.strip().upper())

    # Le payload est soit un texte (à nettoyer), soit un dictionnaire.
    payload = record["payload"]
    if isinstance(payload, str):
        payload = payload.strip()
    normalized["payload"] = payload

    # Description du format du contenu et de la connexion.
    normalized["payload_description"] = route_value(payload)
    normalized["connection_description"] = route_value(
        normalized["connection"]
    )

    # Message lisible construit avec une f-string.
    normalized["message"] = (
        f"{normalized['timestamp'].isoformat()} [{normalized['level']}] "
        f"user={normalized['user_id']} ip={normalized['ip']} "
        f"{payload}"
    )
    return normalized


def has_known_level(record: dict) -> bool:
    """Dire si le niveau de l'événement fait partie des quatre acceptés."""
    if record["level"] in LEVELS:
        return True
    # On prévient, mais le traitement des événements suivants continue.
    print(f"Événement ignoré : niveau inconnu {record['level']!r}")
    return False


def normalize_records(records: Iterable[dict]) -> Iterator[dict]:
    """Nettoyer un flux de dictionnaires puis retirer les niveaux inconnus.

    records peut être une liste de test ou un itérateur venant de P1.
    """
    # map applique normalize_record à chaque événement, à la demande.
    normalized = map(normalize_record, records)
    # Le filtre vient après : " debug " doit d'abord devenir "DEBUG".
    return filter(has_known_level, normalized)


def build_pipeline(
    lines: Iterable[str],
    parser: Callable[[str], dict | None] = parse_line,
) -> Iterator[dict]:
    """Enchaîner les étapes : lignes -> dictionnaires -> événements propres.

    lines  : les lignes de texte fournies par P1, une à la fois.
    parser : la fonction qui transforme une ligne en dictionnaire. Par
             défaut c'est parse_line de P1 ; les tests en passent une autre.
    """
    # 1. filter + lambda : on écarte les lignes vides ou faites d'espaces.
    nonempty_lines = filter(lambda line: line.strip() != "", lines)
    # 2. map : la fonction est passée sans parenthèses, map l'appellera
    #    elle-même pour chaque ligne.
    parsed_records = map(parser, nonempty_lines)
    # 3. filter(None, ...) : retire les None renvoyés pour les lignes
    #    invalides.
    valid_records = filter(None, parsed_records)
    # 4. Normalisation puis filtrage des niveaux inconnus.
    return normalize_records(valid_records)
