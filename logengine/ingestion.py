"""Lecture paresseuse : aucun historique des lignes n'est conservé."""

from collections.abc import Iterable, Iterator
from pathlib import Path


def read_lines(path: str | Path) -> Iterator[str]:
    """Lire en UTF-8 ; les erreurs de fichier restent visibles à l'appelant.

    L'ouverture a lieu au premier next(). Le with ferme le fichier lorsque
    le générateur se termine ou lorsque son consommateur appelle close().
    """
    with open(path, encoding="utf-8") as source:
        for line in source:
            # Suspendre ici, puis reprendre à la prochaine demande.
            yield line


def read_sources(paths: Iterable[str | Path]) -> Iterator[str]:
    """Déléguer à chaque lecteur, dans l'ordre fourni, sans tri global."""
    for path in paths:
        yield from read_lines(path)
