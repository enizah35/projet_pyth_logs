# Projet Python : analyse de logs en flux

Projet ING3 en trinôme, Python 3.10 ou supérieur. Le contrat de données et la
répartition figurent dans [le guide d'équipe](docs/GUIDE_EQUIPE.md).

Le [lien avec les cours](docs/LIEN_AVEC_LES_COURS.md) relie chaque notion aux
supports fournis et aux modules du projet. La base privilégie les fonctions,
les types simples et les étapes explicites, tout en conservant les notions
imposées par l'énoncé.

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

## Commencer la partie P2

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m examples.demo_p2
```

La démonstration traite trois dictionnaires manuels dans deux scénarios :
la règle de blacklist seule (trois événements, une alerte), puis les règles
blacklist et CRITICAL ensemble (trois événements, deux alertes). L'audit JSON
est écrit dans `output/p2/audit.json`.

Les modules P2 sont `logengine/pipeline.py`, `logengine/rules.py` et
`logengine/audit.py`.

## Point d'entrée commun

`main.py` raccorde les fonctions convenues :

```text
read_sources(paths) -> build_pipeline(lines, parser=parse_line)
                   -> apply_security_rules(...) -> analyze(...)
```

Pour lancer dès maintenant la démonstration P2, sans P1 ni P3 :

```powershell
python main.py --demo-p2
```

Ce mode exécute l'exemple P2 décrit ci-dessus et écrit son audit dans
`output/p2/audit.json`. Il n'effectue pas la détection de force brute.
Les options de blacklist, de seuil et d'audit concernent la chaîne complète.

Lorsque P1 aura fourni `logengine/ingestion.py` et `logengine/parsing.py`, et P3
`logengine/analysis.py`, lancer depuis la racine du projet :

```powershell
python main.py data/demo.jsonl --blacklist data/blacklist.txt --threshold 3
python main.py data/fichier1.jsonl data/fichier2.jsonl --threshold 3
```

Sans argument, `python main.py` utilise le jeu de démonstration et la blacklist
du dépôt. `python main.py --help` présente les options. Le seuil doit être positif.
Si un module manque, le programme indique lequel et s'arrête explicitement.

Le bilan P3 est affiché en JSON, y compris ses ensembles d'IP convertis en listes.
Les fichiers sont parcourus dans l'ordre fourni, sans tri ni chargement global.
L'audit est écrit dans `output/audit.json` ; `--audit chemin.json` change sa
destination. La règle CRITICAL facultative reste désactivée.

P1 et P3 conservent les signatures du guide :
`read_sources(paths)`, `parse_line(line)` et
`analyze(records, blacklist=blacklist, threshold=threshold)`.
P1 accepte les espaces et minuscules de `level` : P2 normalise puis filtre
les niveaux inconnus. Il n'est pas nécessaire de modifier `main.py` pour
implémenter les modules de chaque branche.

## Git

Le dépôt commun est `https://github.com/enizah35/projet_pyth_logs`.
Travailler sur une branche `feat/p1-...`, `feat/p2-...` ou `feat/p3-...`, puis
faire relire une pull request vers `main`. Prévenir avant de modifier une
interface ou un fichier appartenant à un autre membre.
