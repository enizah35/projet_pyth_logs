"""Point d'entrée commun : lecture P1 -> nettoyage/règles P2 -> analyse P3.

Trois modes :
- par défaut : chaîne complète, bilan JSON et audit des variables ;
- --details  : diagnostic P1, résultat du parseur ligne par ligne ;
- --demo-p2  : exemple P2 sur trois dictionnaires, sans fichier.
"""

import argparse
from datetime import datetime
import json
import logging
from pathlib import Path
import time
import tracemalloc

from logengine.analysis import analyze
from logengine.audit import export_audit
from logengine.ingestion import read_sources
from logengine.parsing import parse_line, parse_line_details
from logengine.pipeline import build_pipeline
from logengine.rules import apply_security_rules, rule_blacklist


PROJECT_DIR = Path(__file__).resolve().parent


def positive_int(value: str) -> int:
    """Valider le seuil avant de commencer la lecture des fichiers."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("entier positif attendu")
    if number < 1:
        raise argparse.ArgumentTypeError("entier positif attendu")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Décrire les arguments acceptés en ligne de commande."""
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
        "--details", action="store_true",
        help="afficher le résultat du parseur ligne par ligne "
             "(petits fichiers seulement, sans règles ni analyse)",
    )
    parser.add_argument(
        "--measure", action="store_true",
        help="mesurer durée et allocations Python (plus lent)",
    )
    parser.add_argument(
        "--demo-p2", action="store_true",
        help="lancer uniquement l'exemple P2 sur des dictionnaires de test",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Lire les arguments ; argv=None utilise ceux du terminal."""
    return build_parser().parse_args(argv)


def load_blacklist(path: str | Path) -> frozenset[str]:
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
    """Raccorder les modules de l'équipe et consommer le flux une seule fois."""
    # Chaque étape produit un itérateur : aucun fichier complet en liste.
    lines = read_sources(paths)                           # P1
    records = build_pipeline(lines, parser=parse_line)    # P1 + P2
    checked = apply_security_rules(                       # P2
        rule_blacklist, records=records, blacklist=blacklist
    )
    # analyze consomme le flux ; on ne peut pas le parcourir une seconde fois.
    return analyze(checked, blacklist=blacklist, threshold=threshold)  # P3


def show_details(paths: list[Path]) -> int:
    """Diagnostic P1 : afficher ce que le parseur décide pour chaque ligne.

    Retourne le nombre d'événements valides. Seuls des compteurs sont
    conservés, jamais les événements.
    """
    total = 0
    rejected = 0
    empty = 0
    line_count = 0
    # Le numéro de ligne continue d'un fichier au suivant.
    for line_count, line in enumerate(read_sources(paths), start=1):
        if not line.strip():
            empty += 1
            print(f"Ligne {line_count} : ligne vide ignorée")
            continue
        record, reason = parse_line_details(line)
        if record is None:
            rejected += 1
            print(f"Ligne {line_count} : rejetée — {reason}")
        else:
            total += 1
            print(f"Ligne {line_count} : événement valide")

    print("\nLecture terminée")
    print(f"Lignes lues : {line_count}")
    print(f"Événements valides : {total}")
    print(f"Lignes rejetées : {rejected}")
    print(f"Lignes vides ignorées : {empty}")
    return total


def json_value(value: object) -> object:
    """Convertir les ensembles d'IP et les dates pour l'affichage JSON."""
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(
        f"Type non pris en charge dans le bilan : {type(value).__name__}"
    )


def main(argv: list[str] | None = None) -> int:
    """Lire les arguments puis lancer le mode demandé."""
    parser = build_parser()
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

    started = time.perf_counter()
    if args.measure:
        tracemalloc.start()
    try:
        if args.details:
            total = show_details(paths)
        else:
            blacklist = load_blacklist(args.blacklist)
            summary = run_project(paths, blacklist, args.threshold)
            total = summary["total"]
            print(json.dumps(
                summary, ensure_ascii=False, indent=2, default=json_value
            ))
            # globals() et locals() sont appelés ici : l'audit décrit les
            # variables de main.py, pas celles du module audit.
            export_audit(args.audit, globals(), locals())
            print(f"Audit : {args.audit}")
            print(f"Événements valides : {total}")

        if args.measure:
            elapsed = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
            print(f"Durée : {elapsed:.3f} s ; "
                  f"débit : {total / elapsed:.1f} événements/s")
            print(f"Pic allocations Python : {peak} octets (hors RAM totale)")
    except (OSError, UnicodeError) as error:
        logging.error("Lecture ou écriture impossible : %s", error)
        return 1
    finally:
        if args.measure:
            tracemalloc.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
