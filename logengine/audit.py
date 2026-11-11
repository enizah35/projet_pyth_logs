"""P2 : audit des variables d'une portée (globals(), locals()).

Seuls les noms et les types sont exportés, jamais les valeurs.
"""

import json
import os


def describe_scope(scope: dict) -> dict:
    """Associer chaque nom de variable au nom de son type.

    type() ne parcourt pas un générateur : le flux n'est pas consommé.
    """
    types = {}
    for name, value in scope.items():
        types[name] = type(value).__name__
    return types


def export_audit(
    path: str | os.PathLike, global_scope: dict, local_scope: dict
) -> None:
    """Écrire en JSON les types des variables des deux portées reçues.

    L'appelant fournit globals() et locals() : appelés ici, ils
    décriraient ce module et non le code audité.
    """
    report = {
        "globals": describe_scope(global_scope),
        "locals": describe_scope(local_scope),
    }

    folder = os.path.dirname(path)
    if folder != "":
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
