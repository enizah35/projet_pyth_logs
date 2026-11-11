"""P2 : audit des variables présentes dans une portée Python.

globals() renvoie le dictionnaire des variables du module, locals() celui
des variables de la fonction en cours. L'audit écrit dans un fichier JSON
le nom et le type de chacune.
"""

import json
import os


def describe_scope(scope: dict) -> dict:
    """Associer chaque nom de variable au nom de son type.

    Exemple : {"seuil": 3, "ips": {"1.2.3.4"}} donne
              {"seuil": "int", "ips": "set"}.

    Les valeurs ne sont pas exportées : elles peuvent être sensibles, et
    certaines (modules, générateurs) ne s'écrivent pas en JSON. type() ne
    parcourt pas un générateur, donc le flux de logs n'est pas consommé.
    """
    types = {}
    for name, value in scope.items():
        types[name] = type(value).__name__
    return types


def export_audit(
    path: str | os.PathLike, global_scope: dict, local_scope: dict
) -> None:
    """Écrire le rapport d'audit dans le fichier path.

    globals() et locals() sont appelés par le code qui veut être audité,
    puis passés ici :
        export_audit("output/audit.json", globals(), locals())
    Si on les appelait dans cette fonction, on obtiendrait les variables
    de audit.py et non celles de main.py.

    path peut être une chaîne ou un chemin Path (os.PathLike).
    """
    report = {
        "globals": describe_scope(global_scope),
        "locals": describe_scope(local_scope),
    }

    # Créer le dossier de destination s'il n'existe pas encore.
    folder = os.path.dirname(path)
    if folder != "":
        os.makedirs(folder, exist_ok=True)

    # "with" ferme le fichier automatiquement, même en cas d'erreur.
    with open(path, "w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
