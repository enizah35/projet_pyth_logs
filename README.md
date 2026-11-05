# Projet Python : analyse de logs en flux

Projet ING3 en trinôme, Python 3.10 ou supérieur. Le contrat de données et la
répartition figurent dans [le guide d'équipe](docs/GUIDE_EQUIPE.md).

## Répartition

- P1 : lecture, parsing, CLI, environnement et génération du fichier de 10 Go.
- P2 : nettoyage, pipeline fonctionnel, règles de sécurité et audit.
- P3 : statistiques, détection de force brute et assemblage du rapport.

## Données communes

`data/demo.jsonl` contient dix événements valides, une ligne JSON malformée et
une ligne vide. `data/blacklist.txt` contient deux IP de test.

Le fichier de 10 Go sera généré dans `data/generated/`, exclu de Git.
Seuls le générateur, sa commande et les mesures doivent être partagés.

## Installation sous PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Le moteur démarre avec la bibliothèque standard de Python, sans dépendance
externe. Chaque personne utilise son propre environnement virtuel.

## Git

Le dépôt commun est `https://github.com/enizah35/projet_pyth_logs`.
Travailler sur une branche `feat/p1-...`, `feat/p2-...` ou `feat/p3-...`, puis
faire relire une pull request vers `main`. Prévenir avant de modifier une
interface ou un fichier appartenant à un autre membre.
