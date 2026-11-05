"""P2 : export des noms et types des variables d'une portée Python."""

from collections.abc import Mapping
import json
from pathlib import Path


def export_audit(
    path: str | Path,
    global_scope: Mapping[str, object],
    local_scope: Mapping[str, object],
) -> None:
    """Exporter les types, sans dévoiler les valeurs ni consommer de flux.

    Le code appelant fournit globals() et locals() depuis la portée choisie.
    Un appel interne décrirait la portée de l'exporteur, pas celle de main.
    """
    # Chaque portée est un dictionnaire : on parcourt ses paires nom/valeur.
    global_types = {}
    for name, value in global_scope.items():
        global_types[name] = type(value).__name__

    local_types = {}
    for name, value in local_scope.items():
        local_types[name] = type(value).__name__

    report = {"globals": global_types, "locals": local_types}
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
