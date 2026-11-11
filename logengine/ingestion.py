"""P1 : lecture des fichiers de logs, ligne par ligne.

Les lignes sont fournies une à une avec yield : rien n'est conservé.
"""

from collections.abc import Iterable, Iterator
from pathlib import Path


def read_lines(path: str | Path) -> Iterator[str]:
    """Fournir les lignes d'un fichier UTF-8 une par une.

    Le fichier s'ouvre au premier next() et se ferme à la fin du parcours.
    """
    with open(path, encoding="utf-8") as source:
        for line in source:
            # yield : la fonction se met en pause jusqu'à la demande suivante
            yield line


def read_sources(paths: Iterable[str | Path]) -> Iterator[str]:
    """Enchaîner les lignes de plusieurs fichiers, dans l'ordre fourni."""
    for path in paths:
        yield from read_lines(path)
