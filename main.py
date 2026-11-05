"""Point d'entrée commun : lecture P1 -> nettoyage/règles P2 -> analyse P3."""

import argparse
from datetime import datetime
import json
import logging
from pathlib import Path

from logengine.audit import export_audit
from logengine.pipeline import build_pipeline
from logengine.rules import apply_security_rules, rule_blacklist


PROJECT_DIR = Path(__file__).resolve().parent
TEAM_MODULES = {
    "logengine.ingestion": "P1 : read_sources(paths)",
    "logengine.parsing": "P1 : parse_line(line)",
    "logengine.analysis": "P3 : analyze(records, blacklist, threshold)",
}


def positive_int(value: str) -> int:
    """Valider le seuil avant de commencer la lecture des fichiers."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("le seuil doit être supérieur à zéro")
    return number


def load_blacklist(path: Path) -> frozenset[str]:
    """Charger la petite liste d'IP, en ignorant les lignes vides."""
    addresses = set()
    with open(path, "r", encoding="utf-8") as source:
        for line in source:
            address = line.strip()
            if address:
                addresses.add(address)
    # Le frozenset empêche de modifier la blacklist pendant le traitement.
    return frozenset(addresses)


def run_project(
    paths: list[Path], blacklist: frozenset[str], threshold: int
) -> dict:
    """Raccorder les modules de l'équipe et consommer le flux une seule fois.

    Les imports restent ici pour que --help et --demo-p2 fonctionnent même
    avant la livraison de P1 et P3. Aucun traitement de remplacement n'est
    utilisé pour les modules manquants.
    """
    from logengine.ingestion import read_sources
    from logengine.parsing import parse_line
    from logengine.analysis import analyze

    # Les étapes produisent des itérateurs : aucun fichier complet en liste.
    lines = read_sources(paths)
    records = build_pipeline(lines, parser=parse_line)
    checked = apply_security_rules(
        rule_blacklist, records=records, blacklist=blacklist
    )
    # analyze consomme le flux ; on ne pourra pas le parcourir une seconde fois.
    return analyze(checked, blacklist=blacklist, threshold=threshold)


def json_value(value: object) -> object:
    """Afficher aussi les ensembles d'IP et dates renvoyés dans le bilan."""
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(
        f"Type non pris en charge dans le bilan : {type(value).__name__}"
    )


def main(argv: list[str] | None = None) -> int:
    """Lire les arguments, exécuter la chaîne, exporter l'audit et le bilan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", type=Path,
        help="fichiers JSONL chronologiques (défaut : data/demo.jsonl)",
    )
    parser.add_argument(
        "--blacklist", type=Path, default=PROJECT_DIR / "data/blacklist.txt",
        help="fichier contenant une IP par ligne",
    )
    parser.add_argument(
        "--threshold", type=positive_int, default=3,
        help="seuil de force brute (défaut : 3)",
    )
    parser.add_argument(
        "--audit", type=Path, default=PROJECT_DIR / "output/audit.json",
        help="destination de l'audit des noms et types de variables",
    )
    parser.add_argument(
        "--demo-p2", action="store_true",
        help="lancer uniquement l'exemple P2, sans attendre P1 et P3",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s : %(message)s"
    )

    if args.demo_p2:
        if args.paths:
            parser.error(
                "--demo-p2 utilise des dictionnaires de test, "
                "sans fichier d'entrée"
            )
        from examples.demo_p2 import main as demo_p2

        demo_p2()
        return 0

    if args.paths:
        paths = args.paths
    else:
        paths = [PROJECT_DIR / "data/demo.jsonl"]
    try:
        blacklist = load_blacklist(args.blacklist)
        summary = run_project(paths, blacklist, args.threshold)
        report = json.dumps(
            summary, ensure_ascii=False, indent=2, default=json_value
        )
        export_audit(args.audit, globals(), locals())
    except ModuleNotFoundError as error:
        if error.name not in TEAM_MODULES:
            raise
        parser.exit(
            2,
            f"Module manquant : {error.name} ({TEAM_MODULES[error.name]}).\n"
            "Récupérez le module de votre collègue pour lancer la chaîne complète.\n"
            "En attendant : python main.py --demo-p2\n",
        )
    except (OSError, UnicodeError) as error:
        parser.exit(1, f"Erreur de lecture ou d'écriture : {error}\n")

    print(report)
    print(f"Audit : {args.audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
