"""P2 : nettoyage et transformation des événements, un par un.

Le parseur de P1 transforme chaque ligne en dictionnaire (ou None si la
ligne est invalide). Ce module reçoit ces dictionnaires, les nettoie et
élimine ceux qui ne sont pas exploitables.

Rien n'est stocké dans une liste : map() et filter() ne calculent un
élément que lorsque l'étape suivante le demande.
"""

# Les quatre niveaux acceptés. Un frozenset ne peut pas être modifié et le
# test "x in LEVELS" est rapide.
LEVELS = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})


def route_value(value) -> dict:
    """Reconnaître le format d'une valeur avec match-case.

    Trois formats sont attendus dans un log :
    - une chaîne brute, par exemple "Service unavailable" ;
    - un dictionnaire, par exemple {"event": "login", "status": "failure"} ;
    - un tuple de connexion (ip, port, protocole).
    Tout le reste est classé "unknown".
    """
    match value:
        case str():
            return {"kind": "text", "value": value}
        case dict():
            return {"kind": "event", "value": value}
        # Le motif (str(), int(), str()) accepte aussi une liste de trois
        # éléments. La condition après "if" impose un vrai tuple.
        case (str(), int(), str()) if isinstance(value, tuple):
            return {"kind": "connection", "value": value}
        case _:
            # "_" attrape tous les cas restants, comme un else.
            return {"kind": "unknown", "value": value}


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


def normalize_records(records) -> filter:
    """Nettoyer un flux de dictionnaires puis retirer les niveaux inconnus.

    records peut être une liste de test ou un itérateur venant de P1.
    """
    # map applique normalize_record à chaque événement, à la demande.
    normalized = map(normalize_record, records)
    # Le filtre vient après : " debug " doit d'abord devenir "DEBUG".
    return filter(has_known_level, normalized)


def build_pipeline(lines, parser=None) -> filter:
    """Enchaîner les étapes : lignes -> dictionnaires -> événements propres.

    lines  : les lignes de texte fournies par P1, une à la fois.
    parser : la fonction qui transforme une ligne en dictionnaire. Par
             défaut c'est parse_line de P1 ; les tests en passent une autre.
    """
    if parser is None:
        # Import placé ici pour que le reste du module fonctionne même
        # si le fichier de P1 n'est pas encore présent.
        from .parsing import parse_line

        parser = parse_line

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
