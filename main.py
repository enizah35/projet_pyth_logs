"""Démonstration P1 ; le pipeline P2/P3 sera raccordé à sa livraison."""

import argparse
from collections.abc import Sequence
from contextlib import closing
import logging
from pathlib import Path
import time
import tracemalloc

from logengine.ingestion import read_lines, read_sources
from logengine.parsing import parse_line, parse_line_details


def positive_int(value: str) -> int:
    """Valider le seuil au niveau de la CLI."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("entier positif attendu") from error
    if number <= 0:
        raise argparse.ArgumentTypeError("entier positif attendu")
    return number


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--blacklist", type=Path)
    parser.add_argument("--threshold", type=positive_int, default=3)
    parser.add_argument("--details", action="store_true",
                        help="afficher chaque résultat (petits tests seulement)")
    parser.add_argument("--measure", action="store_true",
                        help="mesurer durée et allocations Python (plus lent)")
    return parser.parse_args(argv)


def load_blacklist(path: str | Path) -> frozenset[str]:
    """Charger les IP non vides une seule fois avant le parcours des logs."""
    with closing(read_lines(path)) as lines:
        return frozenset(line.strip() for line in lines if line.strip())


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s: %(message)s"
    )
    started = time.perf_counter()
    if args.measure:
        tracemalloc.start()
    try:
        blacklist = (
            load_blacklist(args.blacklist) if args.blacklist else frozenset()
        )
        # Trois entiers suffisent : ne pas conserver les événements traités.
        total = 0
        rejected = 0
        empty = 0
        line_count = 0
        # Étape P1 : compter directement les résultats du parseur.
        # À l'intégration, build_pipeline recevra read_sources(args.paths).
        print("Lecture et parsing en cours…")
        with closing(read_sources(args.paths)) as lines:
            # Le numéro est global et continue entre les fichiers.
            for line_count, line in enumerate(lines, start=1):
                if not line.strip():
                    empty += 1
                    if args.details:
                        print(f"Ligne {line_count} : ligne vide ignorée")
                    continue

                if args.details:
                    record, reason = parse_line_details(line)
                else:
                    record = parse_line(line)

                if record is None:
                    rejected += 1
                    if args.details:
                        print(f"Ligne {line_count} : rejetée — {reason}")
                else:
                    total += 1
                    if args.details:
                        print(f"Ligne {line_count} : événement valide")

        print("\nLecture terminée")
        print(f"Lignes lues : {line_count}")
        print(f"Événements valides : {total}")
        print(f"Lignes rejetées : {rejected}")
        print(f"Lignes vides ignorées : {empty}")
        print("Mode P1 : normalisation, règles et analyse P2/P3 "
              "non raccordées.")
        print(f"IP blacklistées chargées : {len(blacklist)} ; "
              f"seuil réservé à P3 : {args.threshold}")
        if args.measure:
            elapsed = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
            print(f"Durée : {elapsed:.3f} s ; "
                  f"débit : {total / elapsed:.1f} événements/s")
            print(f"Pic allocations Python : {peak} octets (hors RAM totale)")
    except (OSError, UnicodeError) as error:
        logging.error("Lecture impossible : %s", error)
        return 1
    finally:
        if args.measure:
            tracemalloc.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
