"""P1 : génération d'un gros fichier de logs JSONL reproductible.

Les événements sont écrits un par un, sans liste en mémoire.
"""

import argparse
from collections.abc import Iterator, Sequence
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import json
from pathlib import Path
import random
import time


def generate_records(seed: int = 0) -> Iterator[dict]:
    """Produire sans fin des événements datés, pour 32 utilisateurs fixes."""
    rng = random.Random(seed)
    timestamp = datetime(2026, 11, 5)
    while True:
        user = rng.randrange(32)
        ip = f"192.168.1.{user + 1}"
        payload = (
            {"event": "login", "status": rng.choice(("success", "failure"))}
            if rng.randrange(4) else "Contrôle de santé OK"
        )
        yield {
            "timestamp": timestamp.isoformat(),
            "level": rng.choice(("INFO", " warning ", "ERROR", "CRITICAL")),
            "ip": ip,
            "user_id": f"user_{user}",
            "connection": [ip, 443, "HTTPS"],
            "payload": payload,
        }
        timestamp += timedelta(seconds=1)


def write_logs(output: str | Path, target_bytes: int, seed: int = 0) -> int:
    """Écrire au moins target_bytes octets et renvoyer la taille écrite.

    Refuse d'écraser un fichier ; la dernière ligne reste complète.
    """
    if type(target_bytes) is not int or target_bytes <= 0:
        raise ValueError("target_bytes doit être un entier positif")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    # "x" : échec si le fichier existe déjà
    with output.open("xb") as destination:
        for record in generate_records(seed):
            text = json.dumps(
                record, ensure_ascii=False, separators=(",", ":")
            )
            line = (text + "\n").encode("utf-8")
            written += destination.write(line)
            if written >= target_bytes:
                break
    return written


def size_in_bytes(value: str) -> int:
    """Convertir une taille en Go décimaux en octets, arrondie au-dessus."""
    try:
        size = Decimal(value)
        if not size.is_finite() or size <= 0:
            raise ValueError
        target = size * 1_000_000_000
        return int(target.to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise argparse.ArgumentTypeError(
            "taille finie strictement positive attendue"
        ) from error


def main(argv: Sequence[str] | None = None) -> int:
    """Lire les arguments, écrire le fichier et afficher sa taille."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size-gb", type=size_in_bytes, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    try:
        written = write_logs(args.output, args.size_gb, args.seed)
    except OSError as error:
        parser.exit(1, f"Écriture impossible : {error}\n")
    elapsed = time.perf_counter() - started
    print(f"Taille sur disque : {args.output.stat().st_size} octets ; "
          f"écrits : {written} ; durée : {elapsed:.3f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
